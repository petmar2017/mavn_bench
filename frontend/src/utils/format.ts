/**
 * Utility functions for formatting data
 */

/**
 * Format bytes to a human-readable string with appropriate units
 * @param bytes - The number of bytes
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted string (e.g., "1.23 MB", "456 KB", "789 B")
 */
export function formatFileSize(bytes: number | null | undefined, decimals: number = 2): string {
  if (bytes === null || bytes === undefined || bytes === 0) {
    return '0 B';
  }

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const size = parseFloat((bytes / Math.pow(k, i)).toFixed(dm));

  return `${size} ${sizes[i]}`;
}

/**
 * Format bytes specifically to MB
 * @param bytes - The number of bytes
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted string in MB (e.g., "1.23 MB")
 */
export function formatToMB(bytes: number | null | undefined, decimals: number = 2): string {
  if (bytes === null || bytes === undefined || bytes === 0) {
    return '0 MB';
  }

  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(decimals)} MB`;
}

/**
 * Format a date to a relative time string
 * @param date - The date to format
 * @returns Formatted string (e.g., "2 hours ago", "3 days ago")
 */
export function formatRelativeTime(date: string | Date): string {
  const now = new Date();
  const then = new Date(date);
  const seconds = Math.floor((now.getTime() - then.getTime()) / 1000);

  const intervals = [
    { label: 'year', seconds: 31536000 },
    { label: 'month', seconds: 2592000 },
    { label: 'day', seconds: 86400 },
    { label: 'hour', seconds: 3600 },
    { label: 'minute', seconds: 60 },
    { label: 'second', seconds: 1 }
  ];

  for (const interval of intervals) {
    const count = Math.floor(seconds / interval.seconds);
    if (count >= 1) {
      return count === 1
        ? `${count} ${interval.label} ago`
        : `${count} ${interval.label}s ago`;
    }
  }

  return 'just now';
}