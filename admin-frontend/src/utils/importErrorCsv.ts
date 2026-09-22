export type ImportErrorRow = { row: number; message: string }

function csvEscape(value: string): string {
  return `"${String(value).replace(/"/g, '""')}"`
}

export function buildImportErrorCsv(errors: ImportErrorRow[]): string {
  const lines = ['row,message']
  for (const error of errors) {
    lines.push(`${error.row},${csvEscape(error.message)}`)
  }
  return `\uFEFF${lines.join('\r\n')}\r\n`
}

export function downloadImportErrorCsv(
  errors: ImportErrorRow[],
  filename = 'error.csv',
): void {
  const blob = new Blob([buildImportErrorCsv(errors)], {
    type: 'text/csv;charset=utf-8',
  })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
