import {list,submit,json} from '../../../lib/community';
export const dynamic='force-dynamic';
export async function GET(req:Request){return list(req);}
export async function POST(req:Request){try{return await submit(req);}catch{return json({error:'保存失败，请稍后重试，填写内容仍保留在页面中。'},500);}}
