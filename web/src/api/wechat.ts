import { get, put } from './client'

export function getTemplateSetting(): Promise<{ subscribed: boolean }> {
  return get('/wechat/template-setting')
}

export function updateTemplateSetting(subscribed: boolean): Promise<{ subscribed: boolean }> {
  return put('/wechat/template-setting', { subscribed })
}

export function getTemplateIds(): Promise<{ template_ids: string[] }> {
  return get('/wechat/template-ids')
}
