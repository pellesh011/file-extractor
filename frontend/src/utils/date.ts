import { format as formatDateFn, formatDistanceToNow } from 'date-fns';

function toMoscowTime(date: Date): Date {
  // Convert to Moscow time (UTC+3)
  const offset = 3 * 60 * 60 * 1000; // 3 hours in milliseconds
  return new Date(date.getTime() + offset);
}

export function formatDate(dateString: string | null): string {
  if (!dateString) return '—';
  try {
    const date = new Date(dateString);
    const zoned = toMoscowTime(date);
    return formatDateFn(zoned, 'dd.MM.yyyy HH:mm:ss');
  } catch {
    return dateString;
  }
}

export function formatRelativeTime(dateString: string | null): string {
  if (!dateString) return '—';
  try {
    const date = new Date(dateString);
    return formatDistanceToNow(date, { addSuffix: true });
  } catch {
    return dateString;
  }
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
