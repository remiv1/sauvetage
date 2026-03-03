/**
 * Commandes fournisseurs – Gestion de la modale d'annulation.
 */
document.addEventListener("DOMContentLoaded", () => {
    // Gestion des sections
    const allSections = document.querySelectorAll("section");
    const ordersManagement = document.getElementById("orders-management");
    const ordersCreate = document.getElementById("orders-create");
    const returnsCreate = document.getElementById("returns-create");
    // Boutons d'action de la section de gestion des commandes
    const btnNewOrder   = document.getElementById("new-order");
    const btnNewReturn = document.getElementById("new-return");
    // Boutons d'action de la section de création de commandes
    const btnBackFromCreateOrder = document.getElementById("back-from-create-order");
    const btnValidateCreateOrder = document.getElementById("create-order-validation");
    // Boutons d'action de la section de création de retours
    const btnBackFromCreateReturn = document.getElementById("back-from-create-return");
    const btnValidateCreateReturn = document.getElementById("create-return-validation");

    /* ── Affichage principal ─────────────────────────────────────────────── */
    // Affichage initial : section de gestion des commandes
    ordersManagement.classList.add("active");
    ordersCreate.classList.add("hidden");
    returnsCreate.classList.add("hidden");

    // Nouvelle commande ou nouveau retour : affichage de la section de création
    btnNewOrder.addEventListener("click", () => {
        allSections.forEach(section => section.classList.add("hidden"));
        ordersCreate.classList.remove("hidden");
        ordersCreate.classList.add("active");
    });

    btnNewReturn.addEventListener("click", () => {
        allSections.forEach(section => section.classList.add("hidden"));
        returnsCreate.classList.remove("hidden");
        returnsCreate.classList.add("active");
    });

    /* ── Affichage principal ─────────────────────────────────────────────── */
    // Retour à la section de gestion des commandes
    btnBackFromCreateOrder.addEventListener("click", () => {
        allSections.forEach(section => section.classList.add("hidden"));
        ordersManagement.classList.remove("hidden");
        ordersManagement.classList.add("active");
    });

    btnBackFromCreateReturn.addEventListener("click", () => {
        allSections.forEach(section => section.classList.add("hidden"));
        ordersManagement.classList.remove("hidden");
        ordersManagement.classList.add("active");
    });

    /* ── Validation de la création ──────────────────────────────────────── */
    btnValidateCreateOrder.addEventListener("click", () => {
        // TODO: Ajouter la logique de validation de la création de commande
    });

    btnValidateCreateReturn.addEventListener("click", () => {
        // TODO: Ajouter la logique de validation de la création de retour
    });
});