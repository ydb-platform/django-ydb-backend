# BookStore
The application is a basic table with the following fields: title, author, description, quantity, record_dttm, release_dt and price.
It supports standard operations (Create record, Update record, Delete record, Search by title or author, sort by any fields) on records.

The app works with the YDB.

How to Run:
* Navigate to the application directory (bookstore).
* Run python manage.py makemigrations to create new migration if you need.
* Run python manage.py migrate to apply all database migrations.
* Run python manage.py runserver to start Django's built-in development server.

After launch, the app will be available at http://127.0.0.1:8000/ by default.
