from app import app, db, User
app.app_context().push()
user = User.query.first()  # Берем твоего первого пользователя
user.role = 'admin'
db.session.commit()
exit()