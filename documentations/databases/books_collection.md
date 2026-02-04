# Gestion des stock de livres

```mermaid
erDiagram
    GeneralObjects {
        int id PK
        int supplier_id FK
        string type
        string ean13
        string name
        text description
        datetime created_at
        datetime updated_at
        last_inventory_timestamp datetime
    }
    Books {
        int id PK
        int id_general_object FK
        string author
        string publisher
        string diffuser
        string editor
        string genre
        int publication_year
        int pages
        float price
    }
    Objects {
        int id PK
        int general_object_id FK
        float price
    }
    ObjectStockMovements {
        int id PK
        int general_object_id FK
        string movement_type
        int quantity
        datetime movement_timestamp
        float price_at_movement
        string source
        string destination
        text notes
    }
    Tags {
        int id PK
        string name
        text description
    }
    ObjectTags {
        int id PK
        int general_object_id FK
        int tag_id FK
    }
    Metadata {
        int id PK
        int general_object_id FK
        json semistructured_data
    }
    MediaFiles {
        int id PK
        string file_name
        string file_type
        string alt_text
        bytea file_data
        datetime uploaded_at
        boolean is_principal
    }
    %% Relations
    GeneralObjects ||--o{ Books : "may be a"
    GeneralObjects ||--o{ Objects : "may be a"
    GeneralObjects ||--o{ ObjectStockMovements : "has movements"
    GeneralObjects ||--o{ Metadata : "has metadata"
    MediaFiles ||--o| Metadata : "may be linked to"
    GeneralObjects ||--o{ ObjectTags : "has tags"
    Tags ||--o{ ObjectTags : "is assigned to"
```

## Description des métadonnées

```json
{
  "language": "string",
  "dimensions": {
    "height": "float",
    "width": "float",
    "depth": "float"
  },
  "weight": "float",
  "edition": "string",
  "awards": ["string"],
  "reviews": [
    {
      "reviewer": "string",
      "rating": "float",
      "comment": "string"
    }
  ],
  "links": [
    "string1",
    "string2"
  ]
}
```
