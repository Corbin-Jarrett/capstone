/*
 * 4TB6 Capstone Project - EyeCan
 * ESP code to read UART transmitted message and 
 * output feedback pattern based on user distance to hazards
 * 
 * ESP IDF 5.0
 * Receive a string via RS232
 */

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

#define UART_NUM UART_NUM_1
#define BUFF_SIZE 1024
#define DATA_SIZE 128
#define UART_TX_PIN 17
#define UART_RX_PIN 16
#define BLINK_GPIO 13 // GPIO 13
#define BLINK_PERIOD 1000 // 1 sec
#define DELIMITER ", "

static QueueHandle_t uart_queue;

// Global variables will be read from RPi
int rpi_signal = 0;    
int user_distance = 0; 
int threshold_1 = 0;   // slower pattern 
int threshold_2 = 0;   // faster pattern

// GPIO Initialization
static void configure_led(void)
{
  gpio_reset_pin(BLINK_GPIO);

  // Set the GPIO as a push/pull output 
  gpio_set_direction(BLINK_GPIO, GPIO_MODE_INPUT_OUTPUT);

  // Start GPIO as off 
  gpio_set_level(BLINK_GPIO, false);
}

// Interrupt handler - used for manual interrupt handling
/*static void IRAM_ATTR uart_intr_handler(void *arg) {
  uint8_t data[BUFF_SIZE];

  // Read data from UART
  int len = uart_read_bytes(UART_NUM, data, BUFF_SIZE - 1, 0);
  
  // Queue received data for interrupt to change global variables
  if (len > 0) {
    data[len] = '\0'; // Ensure null termination
    xQueueSendFromISR(uart_queue, data, NULL); // Send data to queue
  }
}*/

// UART Initialization 
void init_RS232()
{
  const uart_port_t uart_num = UART_NUM; 

  // 1 - Setting Communication Parameters
  const uart_config_t uart_config = {             
      .baud_rate = 115200,
      .data_bits = UART_DATA_8_BITS,
      .parity = UART_PARITY_DISABLE,
      .stop_bits = UART_STOP_BITS_1,
      .flow_ctrl = UART_HW_FLOWCTRL_DISABLE};
  uart_param_config(uart_num, &uart_config);
  
  // 2 - Setting Communication Pins
  uart_set_pin(uart_num, UART_TX_PIN, UART_RX_PIN, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);

  // 3 - Driver Installation
  uart_driver_install(uart_num, BUFF_SIZE, BUFF_SIZE, 10, &uart_queue, 0);

  // 4 - Enable RX Interrupts
  //uart_set_rx_full_threshold(uart_num, 10);  // Trigger interrupt when 10 bytes are received
  uart_enable_rx_intr(uart_num);
  //uart_isr_register(uart_num, uart_intr_handler, NULL, ESP_INTR_FLAG_IRAM, NULL); // Depreciated in ESP-IDF 5.0
  //esp_intr_alloc(ETS_UART0_INTR_SOURCE, ESP_INTR_FLAG_IRAM, uart_intr_handler, NULL, NULL); // Manual interrupt allocation
}

static void rx_task(void *task_func_param) //param not used but needed to align with TaskFunction_t type
{
  uart_event_t event;
  int length = 0;
  uint8_t data[DATA_SIZE];
  char data_copy[DATA_SIZE];
  char * token; 
  
  // Set message variables from RPi camera processing
  while (1) {
    if (xQueueReceive(uart_queue, (void *)&event, portMAX_DELAY)) { //(xQueueReceive(uart_queue, data, portMAX_DELAY)) {
      if (event.type == UART_DATA) {
        memset(data, 0, DATA_SIZE);
        length = uart_read_bytes(UART_NUM, data, event.size, pdMS_TO_TICKS(100));
        if (length > 0 && length < DATA_SIZE) {
          data[length] = ',';
          data[length + 1] = '\0';  // Null-terminate for safety
          printf("ESP32 data received: %.*s\n", length, data);

          // Copy data to avoid modifying original buffer
          memset(data_copy, 0, DATA_SIZE);
          strncpy(data_copy, (char*)data, DATA_SIZE - 1);

          // Parse data
          token = strtok(data_copy, DELIMITER);
          if (token != NULL) rpi_signal = atoi(token);
          token = strtok(NULL, DELIMITER); 
          if (token != NULL) user_distance = atoi(token);
          token = strtok(NULL, DELIMITER); 
          if (token != NULL) threshold_1 = atoi(token); 
          token = strtok(NULL, DELIMITER); 
          if (token != NULL) threshold_2 = atoi(token);
          printf("Signal: %d\n", rpi_signal);
          printf("User Distance: %d\n", user_distance);
          printf("Threshold 1: %d\n", threshold_1);
          printf("Threshold 2: %d\n", threshold_2);
        }
      }
      else if (event.type == UART_FIFO_OVF || event.type == UART_BUFFER_FULL) {
        printf("UART Buffer Overflow\n");
        uart_flush_input(UART_NUM);
        xQueueReset(uart_queue);
      }
    }
  }
}

void app_main() {
  int led_state;

  // Configuration
  configure_led();
  init_RS232();
  
  xTaskCreate(rx_task, "uart_rx_task", BUFF_SIZE * 4, NULL, configMAX_PRIORITIES - 1, NULL);
  
  while(1) {
    led_state = gpio_get_level(BLINK_GPIO);

    // Off case and slight delay to prevent useless/extremely close cycles and overuse of CPU
    if (user_distance > threshold_1 || threshold_1 == 0) {
      printf("LED Off\n");
      gpio_set_level(BLINK_GPIO, false);
      // Prevent CPU hogging between app main and interrupt task
      vTaskDelay(pdMS_TO_TICKS(50)); // 50 ms 
      //! can change to 10 for 10 ms if LED responsiveness is slow
      continue;
    }
    // Fastest output case for within smallest threshold
    else if (user_distance <= threshold_2) {
      printf("Blink LED (Closer Threshold)\n");
      gpio_set_level(BLINK_GPIO, !led_state); // switch the LED state
      vTaskDelay((BLINK_PERIOD/4) / portTICK_PERIOD_MS); // wait 1/4 period
    }   
    // Slower output case for between largest and smallest threshold   
    else if (user_distance <= threshold_1) {
      printf("Blink LED (Further Threshold)\n");
      gpio_set_level(BLINK_GPIO, !led_state); // switch the LED state
      vTaskDelay(BLINK_PERIOD / portTICK_PERIOD_MS); // wait 1 period 
    }
  }
}
