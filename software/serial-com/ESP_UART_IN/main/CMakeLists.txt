idf_component_register(SRCS "ESP_UART_IN.c"
                    PRIV_REQUIRES esp_driver_uart esp_driver_gpio
                    INCLUDE_DIRS ".")
