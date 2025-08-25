// MongoDB initialization script
db = db.getSiblingDB('my_database');

// Create collections
db.createCollection('files');

// Create indexes for better performance
db.files.createIndex({ "name": 1 });
db.files.createIndex({ "status": 1 });
db.files.createIndex({ "_id": 1 });

print('Database initialized successfully');
