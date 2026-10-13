/**
 * Meeting module API (B18-M18)
 * 依据: 会议-实现理解.md §2
 */

import { request, type CommonResult } from './request'

export interface Attendees {
  internal: number[]
  external: string[]
}

export interface ActionItemCreate {
  description: string
  assignee_user_id: number
  due_date: string
}

export interface DecisionCreate {
  content: string
}

export interface MeetingMinutesCreateReq {
  title: string
  meeting_date: string
  meeting_room?: string | null
  recorder_user_id?: number | null
  attendees: Attendees
  summary?: string | null
  decisions?: DecisionCreate[]
  action_items?: ActionItemCreate[]
  client_token: string
}

export interface MeetingMinutesUpdateReq extends MeetingMinutesCreateReq {
  base_version: number
}

export interface AppendixCreateReq {
  content: string
}

export interface ActionItemCloseReq {
  close_remark: string
  evidence_url?: string
}

export interface ActionItem {
  id: string
  description: string
  assignee_user_id: string
  assignee_name: string | null
  due_date: string
  status: string
  close_remark: string | null
  evidence_url: string | null
  closed_at: string | null
  overdue_days: number | null
}

export interface Decision {
  id: string
  seq: number
  content: string
}

export interface Appendix {
  id: string
  content: string
  creator_name: string | null
  create_time: string
}

export interface MeetingMinutes {
  id: string
  code: string
  title: string
  meeting_date: string
  meeting_room: string | null
  dept_id: string
  dept_name: string | null
  recorder_user_id: string
  recorder_name: string | null
  attendees: Attendees
  attendee_names: string[]
  summary: string | null
  status: string
  archived_at: string | null
  archived_by: string | null
  archived_by_name: string | null
  create_time: string
  update_time: string
  version: number
  action_item_count: number
  action_item_closed_count: number
  decisions: Decision[]
  action_items: ActionItem[]
  appendices: Appendix[]
}

export interface MeetingMinutesListItem {
  id: string
  code: string
  title: string
  meeting_date: string
  recorder_user_id: string
  recorder_name: string | null
  attendee_names: string[]
  status: string
  archived_at: string | null
  action_item_count: number
  action_item_closed_count: number
}

export interface UnarchivedMinutes {
  minutes_no: string
  meeting_title: string
  meeting_date: string
  recorder_name: string
  hours_since_meeting: number
}

export interface ArchiveRateData {
  total_meetings: number
  archived_count: number
  archive_rate: number
  unarchived_list: UnarchivedMinutes[]
}

export interface ListParams {
  page_no: number
  page_size: number
  title?: string
  status?: string
  meeting_date_start?: string
  meeting_date_end?: string
}

export interface ArchiveRateParams {
  date_range_start?: string
  date_range_end?: string
}

export const meetApi = {
  /**
   * 获取会议纪要列表 (MN-01)
   */
  list(params: ListParams): Promise<CommonResult<{ list: MeetingMinutesListItem[]; total: number }>> {
    return request.get('/admin-api/ims/meet/minutes/list', { params })
  },

  /**
   * 获取会议纪要详情 (MN-08)
   */
  get(id: string): Promise<CommonResult<MeetingMinutes>> {
    return request.get(`/admin-api/ims/meet/minutes/${id}`)
  },

  /**
   * 创建会议纪要 (MN-02, MN-03)
   */
  create(data: MeetingMinutesCreateReq): Promise<CommonResult<{ data: MeetingMinutes; warnings: number[] }>> {
    return request.post('/admin-api/ims/meet/minutes', data)
  },

  /**
   * 更新会议纪要 (MN-03, MN-04)
   */
  update(id: string, data: MeetingMinutesUpdateReq): Promise<CommonResult<{ data: MeetingMinutes; warnings: number[] }>> {
    return request.put(`/admin-api/ims/meet/minutes/${id}`, data)
  },

  /**
   * 归档会议纪要 (MN-05)
   */
  archive(id: string): Promise<CommonResult<{ data: MeetingMinutes; warnings: number[] }>> {
    return request.put(`/admin-api/ims/meet/minutes/${id}/archive`)
  },

  /**
   * 添加附录 (MN-06)
   */
  addAppendix(id: string, data: AppendixCreateReq): Promise<CommonResult<MeetingMinutes>> {
    return request.post(`/admin-api/ims/meet/minutes/${id}/appendix`, data)
  },

  /**
   * 删除会议纪要 (MN-07)
   */
  delete(id: string): Promise<CommonResult> {
    return request.delete(`/admin-api/ims/meet/minutes/${id}`)
  },

  /**
   * 行动项回填 (AI-02)
   */
  closeActionItem(itemId: string, data: ActionItemCloseReq): Promise<CommonResult<ActionItem>> {
    return request.put(`/admin-api/ims/meet/minutes/action-item/${itemId}`, data)
  },

  /**
   * 获取留痕率统计 (ST-01)
   */
  getArchiveRate(params?: ArchiveRateParams): Promise<CommonResult<ArchiveRateData>> {
    return request.get('/admin-api/ims/meet/minutes/archive-rate', { params })
  },
}

export default meetApi
