export const formatQuantity = value => new Intl.NumberFormat('ko-KR').format(Number(value || 0));
export const formatCurrency = (value, currency = 'KRW') => new Intl.NumberFormat('ko-KR', {
  style: 'currency', currency, maximumFractionDigits: currency === 'KRW' ? 0 : 2
}).format(Number(value || 0));
export const formatDate = value => value ? new Intl.DateTimeFormat('ko-KR', {
  month: 'short', day: 'numeric', weekday: 'short'
}).format(new Date(`${value}T00:00:00`)) : '미정';

export function escapeHtml(value = '') {
  return String(value).replace(/[&<>'"]/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[character]));
}
