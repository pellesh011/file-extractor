import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { formatDate } from '../utils/date';

type DownloadStatus = 'idle' | 'running' | 'completed' | 'error';

interface DownloadPageState {
  status: DownloadStatus;
  taskId: string | null;
  startedAt: Date | null;
  receivedFiles: number;
  processedFiles: number;
  totalFiles: number;
  error: string | null;
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'RUNNING':
      return 'status-info';
    case 'COMPLETED':
      return 'status-success';
    case 'FAILED':
      return 'status-error';
    default:
      return '';
  }
}

export function DownloadPage() {
  const [state, setState] = useState<DownloadPageState>({
    status: 'idle',
    taskId: null,
    startedAt: null,
    receivedFiles: 0,
    processedFiles: 0,
    totalFiles: 0,
    error: null,
  });

  const [pollInterval, setPollInterval] = useState<number | null>(null);

  const clearPoll = useCallback(() => {
    if (pollInterval) {
      clearInterval(pollInterval);
      setPollInterval(null);
    }
  }, [pollInterval]);

  const startDownload = async () => {
    clearPoll();
    try {
      const res = await api.startDownload({});
      const taskId = res.task_id;
      const startedAt = new Date();

      setState({
        status: 'running',
        taskId,
        startedAt,
        receivedFiles: 0,
        processedFiles: 0,
        totalFiles: 0,
        error: null,
      });

      const interval = setInterval(async () => {
        if (!taskId) return;
        try {
          const task = await api.getTaskStatus(taskId);
          setState(prev => ({
            ...prev,
            receivedFiles: task.received_files,
            processedFiles: task.processed_files,
            totalFiles: task.received_files,
            status: task.status === 'COMPLETED' ? 'completed' :
                    task.status === 'FAILED' ? 'error' : 'running',
            error: task.error || null,
          }));

          if (task.status === 'COMPLETED' || task.status === 'FAILED') {
            clearPoll();
          }
        } catch (err) {
          console.error('Poll error:', err);
        }
      }, 1000);

      setPollInterval(interval);
    } catch (err) {
      setState(prev => ({
        ...prev,
        status: 'error',
        error: err instanceof Error ? err.message : 'Ошибка запуска',
      }));
    }
  };

  useEffect(() => {
    return () => clearPoll();
  }, [clearPoll]);

  const isRunning = state.status === 'running';
  const isCompleted = state.status === 'completed';
  const isError = state.status === 'error';

  return (
    <div className="page download-page">
      <h1>Скачивание данных</h1>

      <div className="card">
        <div className="card-header">
          <h2>Процесс скачивания</h2>
        </div>
        <div className="card-body">
          {state.status === 'idle' ? (
            <div className="idle-state">
              <p>Нажмите кнопку ниже, чтобы начать скачивание документов из внешнего API.</p>
              <p>Процесс продолжается, пока ручка имён не вернёт пустой ответ.</p>
              <button
                className="btn btn-primary btn-lg"
                onClick={startDownload}
                disabled={isRunning}
              >
                Скачать данные
              </button>
            </div>
          ) : (
            <div className="download-progress">
              <div className="progress-info">
                <div className="info-row">
                  <span className="label">Время старта (НСК):</span>
                  <span className="value">
                    {state.startedAt ? formatDate(state.startedAt.toISOString()) : '—'}
                  </span>
                </div>
                <div className="info-row">
                  <span className="label">Получено названий файлов:</span>
                  <span className="value">{state.totalFiles}</span>
                </div>
                <div className="info-row">
                  <span className="label">Статус:</span>
                  <span className={`status-badge ${getStatusColor(state.status.toUpperCase())}`}>
                    {state.status === 'running' ? 'Скачиваю...' :
                     state.status === 'completed' ? 'Завершено' :
                     state.status === 'error' ? 'Ошибка' : 'Ожидание'}
                  </span>
                </div>
              </div>

              {(state.receivedFiles > 0 || isRunning) && (
                <div className="progress-bar-container">
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{
                        width: `${state.totalFiles > 0
                          ? (state.processedFiles / state.totalFiles) * 100
                          : isRunning ? 50 : 0}%`,
                      }}
                    />
                  </div>
                  <p className="progress-text">
                    {state.processedFiles} из {state.totalFiles} скачано
                  </p>
                </div>
              )}

              {isError && (
                <div className="error-message">
                  Ошибка: {state.error}
                </div>
              )}

              {isCompleted && (
                <div className="success-message">
                  Скачивание завершено! Обработано файлов: {state.processedFiles}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
