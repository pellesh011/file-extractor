import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type { TaskStatusResponse } from '../api/types';
import { formatDate } from '../utils/date';

type DownloadStatus = 'idle' | 'running' | 'blocked' | 'completed' | 'error';

interface DownloadPageState {
  status: DownloadStatus;
  taskId: string | null;
  startedAt: Date | null;
  receivedFiles: number;
  processedFiles: number;
  totalFiles: number;
  error: string | null;
  blockedUntil: string | null;
  blockReason: string | null;
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'RUNNING':
      return 'status-info';
    case 'COMPLETED':
      return 'status-success';
    case 'FAILED':
      return 'status-error';
    case 'BLOCKED':
      return 'status-warning';
    default:
      return '';
  }
}

function statusBadgeClass(status: string): string {
  switch (status) {
    case 'RUNNING':
      return 'running';
    case 'COMPLETED':
      return 'completed';
    case 'FAILED':
      return 'failed';
    case 'BLOCKED':
      return 'blocked';
    default:
      return 'created';
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case 'RUNNING':
      return 'Выполняется';
    case 'COMPLETED':
      return 'Завершено';
    case 'FAILED':
      return 'Ошибка';
    case 'BLOCKED':
      return 'Заблокировано';
    default:
      return status;
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
    blockedUntil: null,
    blockReason: null,
  });

  const [pollInterval, setPollInterval] = useState<number | null>(null);
  const [tasks, setTasks] = useState<TaskStatusResponse[]>([]);
  const [tasksLoading, setTasksLoading] = useState(true);

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
        blockedUntil: null,
        blockReason: null,
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
                    task.status === 'FAILED' ? 'error' :
                    task.status === 'BLOCKED' ? 'blocked' : 'running',
            error: task.error || null,
            blockedUntil: task.blocked_until || null,
            blockReason: task.block_reason || null,
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

  const fetchTasks = useCallback(async () => {
    try {
      const result = await api.getTasks();
      setTasks(result);
    } catch {
      // ignore fetch errors
    } finally {
      setTasksLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  useEffect(() => {
    return () => clearPoll();
  }, [clearPoll]);

  useEffect(() => {
    if (state.status === 'completed' || state.status === 'error' || state.status === 'blocked') {
      fetchTasks();
    }
  }, [state.status, fetchTasks]);

  const isRunning = state.status === 'running';
  const isBlocked = state.status === 'blocked';
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
                     state.status === 'blocked' ? 'Заблокировано' :
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

              {isBlocked && (
                <div className="warning-message">
                  <p><strong>Заблокировано:</strong> {state.blockReason || 'Внешний API недоступен'}</p>
                  {state.blockedUntil && (
                    <p><strong>Возобновится:</strong> {formatDate(state.blockedUntil)}</p>
                  )}
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

      <div className="card" style={{ marginTop: 24 }}>
        <div className="card-header">
          <h2>История скачиваний</h2>
        </div>
        <div className="card-body">
          {tasksLoading ? (
            <div className="loading">Загрузка...</div>
          ) : tasks.length === 0 ? (
            <p style={{ color: '#666' }}>Пока нет скачиваний.</p>
          ) : (
            <>
              <div className="table-responsive">
                <table className="files-table">
                  <thead>
                    <tr>
                      <th>Время старта (НСК)</th>
                      <th>Статус</th>
                      <th>Получено</th>
                      <th>Обработано</th>
                      <th>Ошибка</th>
                      <th>Возобновится</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tasks.map(t => (
                      <tr key={t.task_id}>
                        <td>{formatDate(t.started_at)}</td>
                        <td>
                          <span className={`status-badge ${statusBadgeClass(t.status)}`}>
                            {statusLabel(t.status)}
                          </span>
                        </td>
                        <td>{t.received_files}</td>
                        <td>{t.processed_files}</td>
                        <td style={{ color: '#991b1b', maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {t.error || '—'}
                        </td>
                        <td style={{ maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {t.blocked_until ? formatDate(t.blocked_until) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p style={{ marginTop: 12, fontSize: '0.8125rem', color: '#999' }}>
                Показаны последние 10 скачиваний. Для полной истории обратитесь к администратору.
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
