from app import app, db, User

with app.test_client() as c:
    with app.app_context():
        users = User.query.all()
        for u in users:
            print(f"Testing user {u.full_name}...")
            with c.session_transaction() as sess:
                sess['_user_id'] = str(u.id)
                sess['_fresh'] = True
            
            # Hit /geral
            rv = c.get('/geral')
            if rv.status_code != 200:
                print("Status code:", rv.status_code)
                print(rv.data.decode('utf-8'))
            else:
                print("OK")
