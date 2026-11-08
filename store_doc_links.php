<?php
/**
 * Sets the link buttons of the product pages on ilmtech.in: Documentation, Video Guides and demos.
 * Each button is a product feature (templates/catalog/product.tpl reads them by name).
 * Run in the store root:   php tools/docsite/store_doc_links.php
 * Safe to run again; each product gets its own custom feature value in every language.
 */
if (PHP_SAPI !== 'cli' || !is_file('app/config/parameters.php')) {
    fwrite(STDERR, "run it in the store root\n");
    exit(1);
}
$demoWp = 'https://demo.ilmtech.in/wp/pro/';
$links = [   // feature name => product id => URL
    'Documentation' => [
        1 => 'https://doc.ilmtech.in/prestashop/minimum-maximum-multiple-order-quantity-amount',
        2 => 'https://doc.ilmtech.in/prestashop/ilm-size-chart',
        8 => 'https://doc.ilmtech.in/wordpress/ilm-size-chart-pro',
        11 => 'https://doc.ilmtech.in/wordpress/ilm-size-chart-for-woocommerce',
        14 => 'https://doc.ilmtech.in/prestashop/ilm-ai-chat',
        19 => 'https://doc.ilmtech.in/prestashop/ilm-chat-order-for-whatsapp',
        20 => 'https://doc.ilmtech.in/wordpress/ilm-chat-order-for-whatsapp',
    ],
    'Demo Front' => [20 => $demoWp],
    'Demo Back' => [20 => $demoWp . 'wp-admin/'],
    // only playlists that are Public on YouTube
    'Video Guides' => [
        1 => 'https://www.youtube.com/playlist?list=PLPYTROnNCGQA',
        2 => 'https://www.youtube.com/playlist?list=PLD8_srUnWV3w',
    ],
];
$p = (include 'app/config/parameters.php')['parameters'];
$px = $p['database_prefix'];
$db = new PDO('mysql:host=' . $p['database_host'] . ';port=' . ($p['database_port'] ?: 3306) . ';dbname=' . $p['database_name'] . ';charset=utf8mb4',
    $p['database_user'], $p['database_password'], [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
$col = static fn (string $sql, array $a = []) => ($st = $db->prepare($sql)) && $st->execute($a) ? $st->fetchAll(PDO::FETCH_COLUMN) : [];

$langs = array_map('intval', $col("SELECT id_lang FROM {$px}lang"));
$shops = array_map('intval', $col("SELECT id_shop FROM {$px}shop"));
$db->beginTransaction();
foreach ($links as $name => $urls) {
    $feature = (int) ($col("SELECT id_feature FROM {$px}feature_lang WHERE name = ? AND id_lang = 1", [$name])[0] ?? 0);
    if (!$feature) {
        $position = (int) ($col("SELECT COALESCE(MAX(position) + 1, 0) FROM {$px}feature")[0] ?? 0);
        $db->prepare("INSERT INTO {$px}feature (position) VALUES (?)")->execute([$position]);
        $feature = (int) $db->lastInsertId();
        foreach ($langs as $lang) {
            $db->prepare("INSERT INTO {$px}feature_lang (id_feature, id_lang, name) VALUES (?, ?, ?)")->execute([$feature, $lang, $name]);
        }
        foreach ($shops as $shop) {
            $db->prepare("INSERT INTO {$px}feature_shop (id_feature, id_shop) VALUES (?, ?)")->execute([$feature, $shop]);
        }
    }
    foreach ($urls as $product => $url) {
        $value = (int) ($col("SELECT fp.id_feature_value FROM {$px}feature_product fp JOIN {$px}feature_value fv USING (id_feature_value)
            WHERE fp.id_feature = ? AND fp.id_product = ? AND fv.custom = 1", [$feature, $product])[0] ?? 0);
        if (!$value) {
            $db->prepare("INSERT INTO {$px}feature_value (id_feature, custom) VALUES (?, 1)")->execute([$feature]);
            $value = (int) $db->lastInsertId();
            $db->prepare("INSERT INTO {$px}feature_product (id_feature, id_product, id_feature_value) VALUES (?, ?, ?)")->execute([$feature, $product, $value]);
        }
        foreach ($langs as $lang) {
            $db->prepare("INSERT INTO {$px}feature_value_lang (id_feature_value, id_lang, value) VALUES (?, ?, ?)
                ON DUPLICATE KEY UPDATE value = VALUES(value)")->execute([$value, $lang, $url]);
        }
        echo "product $product: $name -> $url (feature value $value)\n";
    }
}
$db->commit();
