import { env } from 'cloudflare:workers';
import courses from './course-ids.json';
export const json=(body:unknown,status=200)=>Response.json(body,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
export function user(req:Request){return req.headers.get('oai-authenticated-user-id');}
export function checkWrite(req:Request){
 const origin=req.headers.get('origin');
 if(!origin||origin!==new URL(req.url).origin)return json({error:'请从本站提交。'},403);
 if(!user(req))return json({error:'请先登录后再提交；公开展示时不显示登录身份。'},401);
 if(!env.DB||!env.BUCKET)return json({error:'投稿服务暂不可用，请稍后重试。'},503);
 return null;
}
const text=(form:FormData,key:string,max:number)=>String(form.get(key)||'').trim().slice(0,max);
const allowed=['application/pdf','image/png','image/jpeg','text/plain','text/markdown'];
export async function list(req:Request){
 if(!env.DB)return json({error:'投稿服务暂不可用。'},503);
 const courseId=new URL(req.url).searchParams.get('course');
 if(!courseId||!courses.includes(courseId))return json({error:'请选择已收录课程。'},400);
 const rows=await env.DB.prepare('SELECT * FROM community_reviews WHERE course_id=? ORDER BY created_at DESC,id DESC LIMIT 100').bind(courseId).all();
 const results=await Promise.all(rows.results.map(async(r:any)=>{
  const a=await env.DB!.prepare('SELECT id,name,mime,size FROM review_files WHERE review_id=?').bind(r.id).all();
  const {author_id,...publicRow}=r;return {...publicRow,mine:author_id===user(req),files:a.results};
 }));
 return json({reviews:results,limit:100});
}
export async function submit(req:Request){
 const denied=checkWrite(req);if(denied)return denied;
 if(Number(req.headers.get('content-length')||0)>26*1024*1024)return json({error:'附件总量过大。'},413);
 const form=await req.formData(),courseId=text(form,'course',40),teacher=text(form,'teacher',80),term=text(form,'term',20);
 if(!courses.includes(courseId)||!teacher||!/^20\d{2}(春|秋|暑)$/.test(term))return json({error:'请填写课程、教师及学期，例如2026春。'},400);
 const learning=text(form,'learning',5000),workload=text(form,'workload',5000),assessment=text(form,'assessment',5000),grading=text(form,'grading',5000),overall=text(form,'overall',5000);
 if(overall.length<30)return json({error:'综合体验请至少写30字，具体经历更有帮助。'},400);
 if(form.get('consent')!=='yes')return json({error:'请确认公开投稿内容和附件。'},400);
 const uid=user(req)!,since=new Date(Date.now()-86400000).toISOString();
 const count:any=await env.DB!.prepare('SELECT count(*) AS n FROM community_reviews WHERE author_id=? AND created_at>?').bind(uid,since).first();
 if(count.n>=10)return json({error:'24小时内最多提交10篇课评，请稍后再来。'},429);
 const uploads=form.getAll('files').filter((f):f is File=>typeof f!=='string'&&f.size>0);
 if(uploads.length>3||uploads.some(f=>f.size>8*1024*1024))return json({error:'最多3个附件，每个不超过8MB。'},400);
 const rawHours=text(form,'hours',5),hours=rawHours===''?null:Number(rawHours);
 if(hours!==null&&(!Number.isFinite(hours)||hours<0||hours>168))return json({error:'每周用时应为0—168小时。'},400);
 const ready=[];
 for(const f of uploads){
  if(!allowed.includes(f.type))return json({error:'附件支持PDF、PNG、JPG、TXT、Markdown。'},400);
  const bytes=new Uint8Array(await f.arrayBuffer());
  const valid=f.type==='application/pdf'?new TextDecoder().decode(bytes.slice(0,5))==='%PDF-':f.type==='image/png'?bytes[0]===137&&bytes[1]===80&&bytes[2]===78&&bytes[3]===71:f.type==='image/jpeg'?bytes[0]===255&&bytes[1]===216&&bytes[2]===255:!bytes.includes(0);
  if(!valid)return json({error:'附件格式与内容不符，请重新选择。'},400);
  ready.push({id:crypto.randomUUID(),name:f.name.replace(/[\\/\x00-\x1f]/g,'_').slice(0,150),mime:f.type,bytes});
 }
 const id=crypto.randomUUID(),created=new Date().toISOString(),stored:string[]=[];
 try{
  for(const f of ready){const key='reviews/'+id+'/'+f.id;await env.BUCKET!.put(key,f.bytes,{httpMetadata:{contentType:f.mime}});stored.push(key);}
  await env.DB!.batch([
   env.DB!.prepare('INSERT INTO community_reviews (id,course_id,author_id,teacher,term,class_type,nickname,learning,workload,assessment,grading,overall,grade,hours,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)').bind(id,courseId,uid,teacher,term,text(form,'classType',40)||'未注明',text(form,'nickname',30)||'匿名同学',learning,workload,assessment,grading,overall,text(form,'grade',30),hours,created),
   ...ready.map((f,i)=>env.DB!.prepare('INSERT INTO review_files (id,review_id,object_key,name,mime,size) VALUES (?,?,?,?,?,?)').bind(f.id,id,stored[i],f.name,f.mime,f.bytes.length))
  ]);
  return json({id,created_at:created},201);
 }catch(e){await Promise.all(stored.map(k=>env.BUCKET!.delete(k)));throw e;}
}
export async function remove(req:Request,id:string){
 const denied=checkWrite(req);if(denied)return denied;
 const row:any=await env.DB!.prepare('SELECT author_id FROM community_reviews WHERE id=?').bind(id).first();
 if(!row||row.author_id!==user(req))return json({error:'只能删除自己的投稿。'},403);
 const files=await env.DB!.prepare('SELECT object_key FROM review_files WHERE review_id=?').bind(id).all();
 await env.DB!.batch([env.DB!.prepare('DELETE FROM review_files WHERE review_id=?').bind(id),env.DB!.prepare('DELETE FROM community_reviews WHERE id=? AND author_id=?').bind(id,user(req))]);
 await Promise.all(files.results.map((f:any)=>env.BUCKET!.delete(f.object_key)));
 return json({deleted:true});
}
export async function attachment(id:string){
 if(!env.DB||!env.BUCKET)return json({error:'附件服务暂不可用。'},503);
 const f:any=await env.DB.prepare('SELECT f.* FROM review_files f JOIN community_reviews r ON r.id=f.review_id WHERE f.id=?').bind(id).first();
 if(!f)return json({error:'附件不存在或已删除。'},404);
 const object=await env.BUCKET.get(f.object_key);if(!object)return json({error:'附件暂不可用。'},404);
 return new Response(object.body,{headers:{'Content-Type':f.mime,'Content-Disposition':"inline; filename*=UTF-8''"+encodeURIComponent(f.name),'X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'none'; sandbox",'Cache-Control':'private, max-age=60'}});
}
