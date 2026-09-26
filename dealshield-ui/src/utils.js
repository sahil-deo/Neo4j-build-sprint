/**
 * Utility helpers used across components.
 */

export function fmtUsd(val) {
  if (val == null || val === 0) return '$0'
  return '$' + Number(val).toLocaleString('en-US', { maximumFractionDigits: 0 })
}

export function severityColor(severity) {
  switch ((severity || '').toUpperCase()) {
    case 'CRITICAL': return '#fca5a5'
    case 'HIGH':     return '#fcd34d'
    case 'MEDIUM':   return '#93c5fd'
    case 'LOW':      return '#6ee7b7'
    default:         return '#94a3b8'
  }
}
