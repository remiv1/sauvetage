<?php
/**
 * Plugin Name: Allow Internal Media Downloads
 * Description: Autorise WordPress à télécharger des images depuis app-front
 *              (réseau Docker interne sauv-wpwc) en contournant la protection
 *              SSRF pour ce seul hôte de confiance.
 * Author: Rémi Verschuur
 * Version: 1.0
 * Notes: Ce fichier devra être supprimé lors de la mise en production, une fois
 *              que les certificats SSL pourront être configurés.
 */

// Approche 1 : désactive reject_unsafe_urls pour les URL app-front
add_filter(
    'http_request_args',
    static function ( array $args, string $url ): array {
        if ( str_contains( $url, 'app-front' ) ) {
            $args['reject_unsafe_urls'] = false;
        }
        return $args;
    },
    10,
    2
);

// Approche 2 : déclare app-front comme hôte externe de confiance
add_filter(
    'http_request_host_is_external',
    static function ( bool $is_external, string $host ): bool {
        return $is_external || $host === 'app-front';
    },
    10,
    2
);
