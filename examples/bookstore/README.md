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

# Example for rest requests in terminal:

### Add book
curl -X POST http://127.0.0.1:8000/api/books/ \
-H "Content-Type: application/json" \
-d '{
    "title": "New Book",
    "author": "Me",
    "description": "first success try",
    "quantity": 1,
    "price": 100,
    "release_dt": "2023-01-01",
    "limited_edition": true
}'

### Add list of books
curl -X POST http://127.0.0.1:8000/api/books/ \
-H "Content-Type: application/json" \
-d '[
    {
        "title": "Book 1",
        "author": "Author 1",
        "description": "First book description",
        "quantity": 5,
        "price": 250,
        "release_dt": "2023-01-15",
        "limited_edition": false
    },
    {
        "title": "Book 2", 
        "author": "Author 2",
        "description": "Second book description",
        "quantity": 3,
        "price": 300,
        "release_dt": "2023-02-20",
        "limited_edition": true
    },
    {
        "title": "Book 3",
        "author": "Author 3",
        "description": "Third book description",
        "quantity": 10,
        "price": 150,
        "release_dt": "2023-02-20",
        "limited_edition": false
    }
]'

### Get list of books
curl -X GET http://127.0.0.1:8000/api/books/

### Get book by id
curl -X GET http://127.0.0.1:8000/api/books/1/