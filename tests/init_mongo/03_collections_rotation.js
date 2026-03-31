// Créer une fonction de rotation des collections au 31/12 à 22h

const db = db.getSiblingDB('sauvetage_logs');

// Fonction de rotation des collections
function rotateCollections() {
    const currentYear = new Date().getFullYear();
    const nextYear = currentYear + 1;
    
    const collections = [
        { name: nextYear + '-users', ttl: 5 * 365 * 24 * 60 * 60 },
        { name: nextYear + '-logs', ttl: 365 * 24 * 60 * 60 },
        { name: nextYear + '-clients', ttl: 5 * 365 * 24 * 60 * 60 },
        { name: nextYear + '-métiers', ttl: 5 * 365 * 24 * 60 * 60 }
    ];
    
    collections.forEach(function(col) {
        try {
            db.createCollection(col.name, {
                capped: false,
                validator: {
                    $jsonSchema: {
                        bsonType: 'object',
                        required: ['timestamp', 'level', 'message'],
                        properties: {
                            _id: { bsonType: 'objectId' },
                            timestamp: { bsonType: 'date' },
                            level: { enum: ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] },
                            message: { bsonType: 'string' },
                            user_id: { bsonType: 'string' },
                            action: { bsonType: 'string' },
                            resource_type: { bsonType: 'string' },
                            resource_id: { bsonType: 'string' },
                            metadata: { bsonType: 'object' },
                            ip_address: { bsonType: 'string' }
                        }
                    }
                }
            });
            
            db.getCollection(col.name).createIndex(
                { timestamp: 1 },
                { expireAfterSeconds: col.ttl }
            );
            db.getCollection(col.name).createIndex({ level: 1, timestamp: -1 });
            
            print('✓ Collection ' + col.name + ' créée pour rotation');
        } catch (e) {
            print('⚠ Collection ' + col.name + ' existe déjà');
        }
    });
}

// Créer un document de configuration pour le scheduler
try {
    db.getCollection('rotation_config').insertOne({
        _id: 'rotation_schedule',
        enabled: true,
        schedule: '0 22 31 12 *', // 31 décembre à 22h
        last_rotation: new Date(),
        next_rotation: new Date(new Date().getFullYear() + 1, 11, 31, 22, 0, 0),
        function: rotateCollections.toString()
    });
    print('✓ Configuration de rotation créée');
} catch (e) {
    print('⚠ Configuration de rotation existe déjà');
}