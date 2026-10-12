import { request } from '@/api/request'

export function checkFileFormat() {
  return request.post('/admin-api/ims/file/check')
}
