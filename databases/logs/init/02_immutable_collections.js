// Créer les collections immuables pour les logs

const db = db.getSiblingDB('${MONGO_DB_LOGS}');
const currentYear = new Date().getFullYear();

// Définir les configurations des collections avec TTL
const collections = [
    {
        name: currentYear + '-users',
        ttl: 5 * 365 * 24 * 60 * 60, // 5 ans en secondes
        description: 'Logs des utilisateurs - Conservation 5 ans'
    },
    {
        name: currentYear + '-logs',
        ttl: 365 * 24 * 60 * 60, // 1 an en secondes
        description: 'Logs généraux - Conservation 1 an'
    },
    {
        name: currentYear + '-clients',
        ttl: 5 * 365 * 24 * 60 * 60, // 5 ans en secondes
        description: 'Logs des clients - Conservation 5 ans'
    },
    {
        name: currentYear + '-métiers',
        ttl: 5 * 365 * 24 * 60 * 60, // 5 ans en secondes
        description: 'Logs des métiers - Conservation 5 ans'
    }
];

// Créer chaque collection
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
                        timestamp: {
                            bsonType: 'date',
                            description: 'Date et heure du log'
                        },
                        level: {
                            enum: ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                            description: 'Niveau de log'
                        },
                        message: {
                            bsonType: 'string',
                            description: 'Message du log'
                        },
                        user_id: {
                            bsonType: 'string',
                            description: 'ID de l\'utilisateur'
                        },
                        action: {
                            bsonType: 'string',
                            description: 'Action effectuée'
                        },
                        resource_type: {
                            bsonType: 'string',
                            description: 'Type de ressource'
                        },
                        resource_id: {
                            bsonType: 'string',
                            description: 'ID de la ressource'
                        },
                        metadata: {
                            bsonType: 'object',
                            description: 'Données supplémentaires'
                        },
                        ip_address: {
                            bsonType: 'string',
                            description: 'Adresse IP'
                        }
                    }
                }
            }
        });
        
        // Créer l'index TTL
        db.getCollection(col.name).createIndex(
            { timestamp: 1 },
            { expireAfterSeconds: col.ttl }
        );
        
        // Créer un index pour les recherches
        db.getCollection(col.name).createIndex({ level: 1, timestamp: -1 });
        db.getCollection(col.name).createIndex({ user_id: 1, timestamp: -1 });
        
        print('✓ Collection ' + col.name + ' créée - ' + col.description);
    } catch (e) {
        print('⚠ Collection ' + col.name + ' existe déjà');
    }
});
