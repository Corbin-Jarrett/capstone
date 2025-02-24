idf_component_register(SRCS "esp_server.c"
                       PRIV_REQUIRES bt nvs_flash esp_driver_gpio
                       INCLUDE_DIRS ".")
