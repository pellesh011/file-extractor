import { formatDistanceToNow } from 'date-fns';
import { formatInTimeZone } from 'date-fns-tz';

export function formatDate(dateString: string | null): string {
  if (!dateString) return '—';
  try {
    return formatInTimeZone(new Date(dateString), 'Europe/Moscow', 'dd.MM.yyyy HH:mm:ss');
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
