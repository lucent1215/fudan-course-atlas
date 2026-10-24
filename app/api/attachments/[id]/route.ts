import {attachment} from '../../../../lib/community';
export const dynamic='force-dynamic';
export async function GET(req:Request,{params}:{params:Promise<{id:string}>}){return attachment((await params).id);}
