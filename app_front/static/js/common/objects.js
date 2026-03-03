/**
 * Module de classes d'objets génériques
 *  - GeneralObject : classe de base pour les objets génériques
 *  - Book : classe de base pour les livres
 *  - OtherObject : classe de base pour les autres objets
 *  - Tags : classe de base pour les mots-clés
 *  - Metadatas : classe de base pour les métadonnées
 * @file objects.js
 * @version 1.0.0
 * @namespace objects
 * @module objects
 * @author [Rémi Verschuur](mailto:rverschuur@audit-io.fr)
 */

/**
 * Classe de base pour les objets génériques
 * @class GeneralObject
 * @constructor
 * @param {Object} data - Les données de l'objet générique
 * @param {number} data.id - L'identifiant de l'objet générique
 * @param {number} data.supplierId - L'identifiant du fournisseur de l'objet générique
 * @param {string} data.generalObjectType - Le type de l'objet générique
 * @param {string} data.ean13 - Le code EAN13 de l'objet générique
 * @param {string} data.name - Le nom de l'objet générique
 * @param {string} data.description - La description de l'objet générique
 * @param {number} data.price - Le prix de l'objet générique
 * @method getName - Retourne le nom de l'objet générique
 * @method applyDiscount - Applique une remise au prix de l'objet générique
 */
class GeneralObject {
    constructor(data) {
        this.id = data.id || null;
        this.supplierId = data.supplierId;
        this.generalObjectType = data.generalObjectType;
        this.ean13 = data.ean13;
        this.name = data.name;
        this.description = data.description;
        this.price = data.price;
    }
    getName() {
        return this.name;
    }
    applyDiscount(discount) {
        this.price = this.price * (1 - discount);
    }
}

/**
 * Classe de base pour les livres
 * @class Book
 * @extends GeneralObject
 * @constructor
 * @param {Object} data - Les données du livre
 * @param {number} data.id_book - L'identifiant du livre
 * @param {string} data.author - L'auteur du livre
 * @param {string} data.diffuser - Le diffuseur du livre
 * @param {string} data.editor - L'éditeur du livre
 * @param {string} data.genre - Le genre du livre
 * @param {number} data.publicationYear - L'année de publication du livre
 * @param {number} data.pages - Le nombre de pages du livre
 */
export class Book extends GeneralObject {
    constructor(data) {
        super(data);
        this.id_book = data.id_book || null;
        this.author = data.author;
        this.diffuser = data.diffuser;
        this.editor = data.editor;
        this.genre = data.genre;
        this.publicationYear = data.publicationYear;
        this.pages = data.pages;
    }
}

/**
 * Classe de base pour les autres objets
 * @class OtherObject
 * @extends GeneralObject
 * @constructor
 * @param {Object} data - Les données de l'autre objet
 * @param {number} data.id_other_object - L'identifiant de l'autre objet
 */
export class OtherObject extends GeneralObject {
    constructor(data) {
        super(data);
        this.id_other_object = data.id_other_object || null;
    }
}

/**
 * Classe de base pour les mots-clés
 * @class Tags
 * @constructor
 * @param {Object} data - Les données du mot-clé
 * @param {number} data.id - L'identifiant du mot-clé
 * @param {string} data.name - Le nom du mot-clé
 * @param {string} data.description - La description du mot-clé
 * @param {number} [data.qté=0] - La quantité du mot-clé
 * @method addQty - Ajoute une quantité au mot-clé
 * @method delQty - Supprime une quantité du mot-clé
 */
export class Tags {
    #qty;
    constructor(data) {
        this.id = data.id || null;
        this.name = data.name;
        this.description = data.description;
        this.#qty = data.qté || 0;
    }
    addQty(qty) {
        this.#qty += qty;
    }
    delQty(qty) {
        if (this.#qty - qty < 0) {
            this.#qty = 0;
        } else {
            this.#qty -= qty;
        }
    }
    getQty() {
        return this.#qty;
    }
}

/**
 * Classe de base pour les métadonnées
 * @class Metadatas
 * @constructor
 * @param {Object} data - Les données de la métadonnée
 * @param {number} data.id - L'identifiant de la métadonnée
 * @param {string} data.name - Le nom de la métadonnée
 * @param {string} data.description - La description de la métadonnée
 * @method addKey - Ajoute une clé à la métadonnée
 * @method delKey - Supprime une clé de la métadonnée
 * @method toJSON - Convertit la métadonnée en JSON
 */
export class Metadatas {
    #pairs={};
    constructor(data) {
        this.id = data.id || null;
        this.GeneralObjectId = data.GeneralObjectId || null;
        if (data.values) {
            this.#pairs = { ...data.values };
        }
    }
    addKey(key, value) {
        this.#pairs[key] = value;
    }
    delKey(key) {
        delete this.#pairs[key];
    }
    prepareForAPI() {
        return {
            id: this.id,
            general_object_id: this.GeneralObjectId,
            obj_metadatas: { ...this.#pairs }
        }
    }
}