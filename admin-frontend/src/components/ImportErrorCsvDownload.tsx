import { DownloadOutlined } from '@ant-design/icons'
import { Button } from 'antd'
import { downloadImportErrorCsv, type ImportErrorRow } from '../utils/importErrorCsv'

export function ImportErrorCsvDownload({ errors }: { errors: ImportErrorRow[] }) {
  if (errors.length === 0) return null

  return (
    <Button
      icon={<DownloadOutlined />}
      onClick={() => downloadImportErrorCsv(errors)}
      style={{ marginTop: 16 }}
    >
      Unduh error.csv
    </Button>
  )
}
