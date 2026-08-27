class UserContext:
 def current_user_id(self):raise NotImplementedError
class FlaskUserContext(UserContext):
 def current_user_id(self):
  from flask import session
  v=session.get('user_id')
  if v is None:
   x=session.get('user');v=x.get('id') if isinstance(x,dict) else None
  try:return int(v) if v is not None else None
  except (TypeError,ValueError):return None
