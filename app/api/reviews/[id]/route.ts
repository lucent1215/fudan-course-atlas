import {remove} from '../../../../lib/community';
export const dynamic='force-dynamic';
export async function DELETE(req:Request,{params}:{params:Promise<{id:string}>}){return remove(req,(await params).id);}
