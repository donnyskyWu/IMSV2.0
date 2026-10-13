/** 工作台问候。5/11/13/18 为既有边界，0 点至 5 点前为凌晨好。 */
export function greetingForHour(hour: number): string {
  if (hour < 5) return '凌晨好'
  if (hour < 11) return '早上好'
  if (hour < 13) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
}
