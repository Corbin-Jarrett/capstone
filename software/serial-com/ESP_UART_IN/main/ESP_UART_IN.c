/*
 * 4TB6 Capstone Project - EyeCan
 * ESP code to read UART transmitted message and 
 * output feedback pattern based on user distance to hazards
 * 
 */
// ESP IDF 5.0
// Receive a string via RS232

#include <stdio.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "esp_log.h"
#include "driver/uart.h"
#include "soc/uart_struct.h"
#include "string.h"
#include "driver/gpio.h"

#define UART_0_TX 1
#define UART_0_RX 3
#define BLINK_GPIO 13 // GPIO 13
#define BLINK_PERIOD 1000 // 1 sec
#define DELIMITER ", "

// will be read from RPI
int rpi_signal;    
int user_distance; 
int threshold_1;   // slower pattern 
int threshold_2;   // faster pattern

static void configure_led(void)
{
    gpio_reset_pin(BLINK_GPIO);
    /* Set the GPIO as a push/pull output */
    gpio_set_direction(BLINK_GPIO, GPIO_MODE_OUTPUT);
    /* Start GPIO as off */
    gpio_set_level(BLINK_GPIO, false);
}

void init_RS232()
{
    const uart_port_t uart_num = UART_NUM_0;
    const int uart_buffer_size = 1024;
    QueueHandle_t uart_queue;

    // 1 - Setting Communication Parameters
    const uart_config_t uart_config = {             
        .baud_rate = 115200,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE};
    uart_param_config(uart_num, &uart_config);
    
    // 2 - Setting Communication Pins
    uart_set_pin(uart_num, UART_0_TX, UART_0_RX, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);

    // 3 - Driver Installation
    uart_driver_install(uart_num, uart_buffer_size, uart_buffer_size, 10, &uart_queue, 0);
}

static void rx_task(void *task_func_param) //param not used but needed to align with TaskFunction_t type
{
    const uart_port_t uart_num = UART_NUM_0;
    int length = 0;
    uint8_t data[128];
    char data_copy[128];
    char * token;

    while (1)
    {   
        user_distance = 0;
        threshold_1 = 0;
        threshold_2 = 0;
        memset(data, 0, sizeof(data));

        uart_get_buffered_data_len(uart_num, (size_t *)&length); // Read data string length
        uart_read_bytes(uart_num, data, length, 100); // Read data string from the buffer
        printf("ESP32 data received: %.*s\n", length, data);
        //vTaskDelay(1000 / portTICK_PERIOD_MS); no delay - read UART receiver as fast as possible
        if (data[0] != 0) {
          memset(data_copy, 0, sizeof(data_copy));
          strcpy(data_copy, (char*)data);
          // do string tokens
          token = strtok(data_copy, DELIMITER);
          rpi_signal = atoi(token);
          token = strtok(NULL, DELIMITER); 
          user_distance = atoi(token);
          token = strtok(NULL, DELIMITER); 
          threshold_1 = atoi(token); 
          token = strtok(NULL, DELIMITER); 
          threshold_2 = atoi(token); 
          printf("Signal: %d\n", rpi_signal);
          printf("User Distance: %d\n", user_distance);
          printf("Threshold 1: %d\n", threshold_1);
          printf("Threshold 2: %d\n", threshold_2);
          if (user_distance <= threshold_2) {
            printf("Blink LED (Closer Threshold)\n");
            gpio_set_level(BLINK_GPIO, true); // turn the LED on 
            vTaskDelay((BLINK_PERIOD/3) / portTICK_PERIOD_MS); // wait 1/3 period
            gpio_set_level(BLINK_GPIO, false); 
            vTaskDelay((BLINK_PERIOD/3) / portTICK_PERIOD_MS);
            gpio_set_level(BLINK_GPIO, true); 
            vTaskDelay((BLINK_PERIOD/3) / portTICK_PERIOD_MS); 
            gpio_set_level(BLINK_GPIO, false);
          }        
          else if (user_distance <= threshold_1) {
            printf("Blink LED (Further Threshold)\n");
            gpio_set_level(BLINK_GPIO, true); // turn the LED on 
            vTaskDelay(BLINK_PERIOD / portTICK_PERIOD_MS); // wait 1 period
            gpio_set_level(BLINK_GPIO, false); 
          }
        }
    }
}

void app_main() {
    configure_led();
    
    printf("--- Receiving Data ---\n");
    vTaskDelay(1000 / portTICK_PERIOD_MS);

    init_RS232();
    xTaskCreate(rx_task, "uart_rx_task", 1024 * 2, NULL, configMAX_PRIORITIES - 1, NULL);
}