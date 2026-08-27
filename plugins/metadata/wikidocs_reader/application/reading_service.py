from ..domain.ports import ProgressStore,UserBookStore
class ReadingService:
 def __init__(self,progress:ProgressStore,users:UserBookStore):self.progress,self.users=progress,users
 def _owned(self,u,b):return self.users.contains(u,b)
 def get_progress(self,u,b):return self.progress.get(u,b) if self._owned(u,b) else None
 def save_position(self,u,b,pid,pos,read,total):
  if not self._owned(u,b):raise PermissionError('책을 찾을 수 없습니다.')
  self.progress.save(u,b,pid,pos,read,total)
 def complete(self,u,b,total):self.save_position(u,b,None,1.0,total,total)
 def mark_unread(self,u,b):
  if not self._owned(u,b):raise PermissionError('책을 찾을 수 없습니다.')
  self.progress.mark_unread(u,b)
 def recent(self,u,limit=20):return self.progress.recent(u,limit)
