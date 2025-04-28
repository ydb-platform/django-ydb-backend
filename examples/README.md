# SimpleCrud
The application is a basic table with the following fields: Name, Description, Quantity, and Created At.
It supports standard CRUD operations (Create, Update, Delete) on records.

The app works with the YDB.

How to Run:
* Navigate to the application directory (simplecrud).
* Run python manage.py migrate to apply all database migrations.
* Run python manage.py runserver to start Django's built-in development server.

After launch, the app will be available at http://127.0.0.1:8000/ by default.