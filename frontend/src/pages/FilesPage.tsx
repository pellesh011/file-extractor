import { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '../api/client';
import { formatDate, formatFileSize } from '../utils/date';
import { formatNumber } from '../utils/calculations';
import { FileItem } from '../api/types';

interface FilesPageState {
  files: FileItem[];
  total: number;
  page: number;
  perPage: number;
  loading: boolean;
  error: string | null;
}

interface SelectedFiles {
  all: boolean;
  page: Set<string>;
  individual: Set<string>;
}

export function FilesPage() {
  const [state, setState] = useState<FilesPageState>({
    files: [],
    total: 0,
    page: 1,
    perPage: 20,
    loading: true,
    error: null,
  });

  const [selection, setSelection] = useState<SelectedFiles>({
    all: false,
    page: new Set(),
    individual: new Set(),
  });

  const [showStats, setShowStats] = useState(false);
  const [stats, setStats] = useState<{
    overall: Record<string, number>;
    perFile: Record<string, Record<string, number>>;
  } | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [statsError, setStatsError] = useState<string | null>(null);

  const loadFiles = useCallback(async (page: number, perPage: number) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const res = await api.getFiles({ page, per_page: perPage });
      setState(prev => ({
        ...prev,
        files: res.items,
        total: res.total,
        page: res.page,
        perPage: res.per_page,
        loading: false,
      }));
      // Reset page selection on page change
      setSelection(prev => ({ ...prev, page: new Set(), all: false }));
    } catch (err) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : 'Ошибка загрузки',
      }));
    }
  }, []);

  useEffect(() => {
    loadFiles(state.page, state.perPage);
  }, [loadFiles, state.page, state.perPage]);

  // Determine selected file IDs
  const selectedFileIds = useMemo(() => {
    if (selection.all) {
      // All files across all pages
      return state.files.map(f => f.id);
    }
    const ids = new Set([...selection.individual]);
    selection.page.forEach(id => ids.add(id));
    return Array.from(ids);
  }, [selection, state.files]);

  const selectedCount = selectedFileIds.length;
  const hasSelection = selectedCount > 0;

  const handleSelectPage = (checked: boolean) => {
    setSelection(prev => ({
      ...prev,
      page: checked ? new Set(state.files.map(f => f.id)) : new Set(),
      all: false,
    }));
  };

  const handleSelectOne = (fileId: string, checked: boolean) => {
    setSelection(prev => {
      const newPage = new Set(prev.page);
      const newIndividual = new Set(prev.individual);

      if (checked) {
        newPage.add(fileId);
        newIndividual.add(fileId);
      } else {
        newPage.delete(fileId);
        newIndividual.delete(fileId);
      }

      return {
        ...prev,
        page: newPage,
        individual: newIndividual,
        all: false,
      };
    });
  };

  const isFileSelected = (fileId: string) => {
    if (selection.all) return true;
    return selection.page.has(fileId) || selection.individual.has(fileId);
  };

  const handleCalculateStats = async () => {
    if (!hasSelection) return;

    setStatsLoading(true);
    setStatsError(null);

try {
        // The frontend calculates locally since we have the files loaded
        // But we need to fetch content from backend
        const res = await api.calculateStats(selectedFileIds);
        setStats({
          overall: res.overall,
          perFile: res.per_file,
        });
        setShowStats(true);
    } catch (err) {
      setStatsError(err instanceof Error ? err.message : 'Ошибка расчёта');
    } finally {
      setStatsLoading(false);
    }
  };

  const handleCloseStats = () => {
    setShowStats(false);
    setStats(null);
    setStatsError(null);
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= Math.ceil(state.total / state.perPage)) {
      setState(prev => ({ ...prev, page: newPage }));
    }
  };

  const handlePerPageChange = (newPerPage: number) => {
    setState(prev => ({ ...prev, page: 1, perPage: newPerPage }));
  };

  const totalPages = Math.ceil(state.total / state.perPage);

  return (
    <div className="page files-page">
      <h1>Скачанные файлы и расчёты</h1>

      {state.error && (
        <div className="alert alert-error">{state.error}</div>
      )}

      <div className="card">
        <div className="card-header">
          <h2>Файлы ({state.total})</h2>
        </div>
        <div className="card-body">
          <div className="table-toolbar">
            <div className="selection-info">
              {hasSelection && (
                <span>
                  Выбрано: <strong>{selectedCount}</strong> из {state.total}
                </span>
              )}
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <select
                value={state.perPage}
                onChange={e => handlePerPageChange(Number(e.target.value))}
                className="btn btn-secondary"
                style={{ padding: '8px 12px' }}
              >
                <option value={20}>20 на странице</option>
                <option value={50}>50 на странице</option>
                <option value={100}>100 на странице</option>
              </select>
            </div>
          </div>

          {state.loading ? (
            <div className="loading">Загрузка...</div>
          ) : state.files.length === 0 ? (
            <p style={{ textAlign: 'center', color: '#666', padding: '40px' }}>
              Файлов пока нет. Нажмите «Скачать данные» на главной странице.
            </p>
          ) : (
            <>
              <div className="table-responsive">
                <table className="files-table">
                  <thead>
                    <tr>
                      <th style={{ width: '40px' }}>
                        <input
                          type="checkbox"
                          checked={state.files.length > 0 && state.files.every(f => isFileSelected(f.id))}
                          onChange={e => handleSelectPage(e.target.checked)}
                          aria-label="Выбрать все на странице"
                        />
                      </th>
                      <th>Имя файла</th>
                      <th>Размер</th>
                      <th>Статус</th>
                      <th>Время скачивания</th>
                    </tr>
                  </thead>
                  <tbody>
                    {state.files.map(file => (
                      <tr key={file.id}>
                        <td>
                          <input
                            type="checkbox"
                            checked={isFileSelected(file.id)}
                            onChange={e => handleSelectOne(file.id, e.target.checked)}
                          />
                        </td>
                        <td style={{ fontFamily: 'monospace', fontSize: '0.8125rem' }}>
                          {file.filename}
                        </td>
                        <td>{formatFileSize(file.size)}</td>
                        <td>
                          <span className={`status-badge ${file.status.toLowerCase()}`}>
                            {file.status}
                          </span>
                        </td>
                        <td>{formatDate(file.uploaded_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {totalPages > 1 && (
                <div className="pagination">
                  <button
                    className="btn btn-secondary"
                    onClick={() => handlePageChange(state.page - 1)}
                    disabled={state.page === 1}
                  >
                    ← Назад
                  </button>
                  <span className="page-info">
                    Страница {state.page} из {totalPages}
                  </span>
                  <button
                    className="btn btn-secondary"
                    onClick={() => handlePageChange(state.page + 1)}
                    disabled={state.page === totalPages}
                  >
                    Вперёд →
                  </button>
                </div>
              )}

              {hasSelection && (
                <div style={{ marginTop: '24px', textAlign: 'right' }}>
                  <button
                    className="btn btn-primary"
                    onClick={handleCalculateStats}
                    disabled={statsLoading}
                  >
                    {statsLoading ? 'Расчёт...' : 'Произвести расчёты'}
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Stats Modal */}
      {showStats && stats && (
        <div className="modal-overlay" onClick={handleCloseStats}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Результаты расчётов</h3>
              <button className="modal-close" onClick={handleCloseStats}>
                ×
              </button>
            </div>
            <div className="modal-body">
              {statsError && (
                <div className="alert alert-error">{statsError}</div>
              )}

              <div className="stats-section">
                <h4>Общая статистика</h4>
                <table className="stats-table">
                  <thead>
                    <tr>
                      <th>Цифра</th>
                        {[...Array(10)].map((_, i) => (
                          <th key={i}><strong>{i}</strong></th>
                        ))}
                    </tr>
                  </thead>
                  <tbody>
                      <tr>
                         <th>Количество</th>
                         {[...Array(10)].map((_, i) => (
                        <td  key={i}>{formatNumber(stats.overall[i.toString()] || 0)}</td>
                        ))}
                      </tr>
                  </tbody>
                </table>
              </div>

              <div className="stats-section">
                <h4>Статистика по файлам</h4>
                <div className="file-stats-scroll">
                  <table className="stats-table">
                    <thead>
                      <tr>
                        <th>Файл</th>
                        {[...Array(10)].map((_, i) => <th key={i} style={{ textAlign: 'center' }}>{i}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(stats.perFile).map(([filename, counts]) => (
                        <tr key={filename}>
                          <td className="filename" title={filename}>{filename}</td>
                          {[...Array(10)].map((_, i) => (
                            <td key={i} style={{ textAlign: 'center' }}>
                              {formatNumber(counts[i.toString()] || 0)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={handleCloseStats}>
                Закрыть
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
