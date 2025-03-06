/*
 * 4TB6 Capstone Project - EyeCan
 * ESP code to create BLE server
 * 
 * ESP IDF 5.4
 */

#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_event.h"
#include "nvs_flash.h"
#include "esp_log.h"
#include "esp_nimble_hci.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"
#include "sdkconfig.h"
#include "driver/gpio.h"

#define LED_GPIO 13 // GPIO 13
#define BLINK_PERIOD 1000 // 1 sec
#define DELIMITER ", "
#define KEEP_ALIVE_INTERVAL_MS 5000  // Send keep-alive every 5 seconds

char *TAG = "BLE-Server-EyeCan";
uint8_t ble_addr_type;

struct ble_gap_adv_params adv_params;
bool status = false;

static uint16_t conn_id = 1;  // connection ID when client connects

// Global variables will be read from RPi
static int rpi_signal = -1;    
static int user_distance = -1; 
static int threshold_1 = -1;   // slower pattern 
static int threshold_2 = -1;   // faster pattern

// GPIO Initialization
static void configure_led(void) {
  gpio_reset_pin(LED_GPIO);

  // Set the GPIO as a push/pull output 
  gpio_set_direction(LED_GPIO, GPIO_MODE_INPUT_OUTPUT);

  // Start GPIO as off 
  gpio_set_level(LED_GPIO, false);
}

void ble_app_advertise(void);

// Write data to ESP32 defined as server
static int device_write(uint16_t conn_handle, uint16_t attr_handle, struct ble_gatt_access_ctxt *ctxt, void *arg) {
    uint8_t *bin_data = ctxt->om->om_data;
    int len = ctxt->om->om_len;
    char *str_data = malloc(len + 1);

    if (str_data != NULL) { // malloc sucess check
        memcpy(str_data, bin_data, len);  
        str_data[len] = ',';      // delimiter
        str_data[len + 1] = '\0'; // null termination
    }

    printf("Data from the client: %.*s\n", len, str_data);

    // Reset global variables
    rpi_signal = -1;    
    user_distance = -1; 
    threshold_1 = -1;   // slower pattern 
    threshold_2 = -1;   // faster pattern

    // Copy data to avoid modifying original buffer
    char str_data_copy[len];
    memset(str_data_copy, 0, len);
    strncpy(str_data_copy, (char*)str_data, len - 1);

    // Parse data
    char * token;
    token = strtok(str_data_copy, DELIMITER);
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

    free(str_data);
    return 0;
}

// Read data from ESP32 defined as server
static int device_read(uint16_t con_handle, uint16_t attr_handle, struct ble_gatt_access_ctxt *ctxt, void *arg) {
    os_mbuf_append(ctxt->om, "Data from the server", strlen("Data from the server"));
    return 0;
}

// Array of pointers to other service definitions
// UUID - Universal Unique Identifier
static const struct ble_gatt_svc_def gatt_svcs[] = {
    {.type = BLE_GATT_SVC_TYPE_PRIMARY,
    .uuid = BLE_UUID16_DECLARE(0x181A), // Define UUID for device type
    .characteristics = (struct ble_gatt_chr_def[]) {
        {.uuid = BLE_UUID16_DECLARE(0xFEF4), // Define UUID for reading
        .flags = BLE_GATT_CHR_F_READ,
        .access_cb = device_read},
        {.uuid = BLE_UUID16_DECLARE(0xDEAD), // Define UUID for writing
        .flags = BLE_GATT_CHR_F_WRITE,
        .access_cb = device_write},
        {0}}},
    {0}
};


void send_keep_alive(void *arg) {
    while(1) {
        if (conn_id != 1) {  // if connected
            struct os_mbuf *om = ble_hs_mbuf_from_flat("KEEP ALIVE", 10);  
            int return_code = ble_gattc_notify_custom(conn_id, 0xFEF4, om);
            if (return_code == 0) {
                ESP_LOGI("BLE", "Sent Keep-Alive Message");
            }
            else {
                if (return_code == BLE_HS_ENOTCONN) {
                    ESP_LOGW("BLE", "Failed to send Keep-Alive: Lost Connection");
                }
                else {
                    ESP_LOGE("BLE", "Failed to send Keep-Alive, error: %d", return_code);
                }
            }
        }
        vTaskDelay(pdMS_TO_TICKS(KEEP_ALIVE_INTERVAL_MS));  // wait for next keep-alive
    }
}


// BLE event handling
static int ble_gap_event(struct ble_gap_event *event, void *arg) {  
    switch (event->type) {
    // Advertise if connected
    case BLE_GAP_EVENT_CONNECT:
        ESP_LOGI("GAP", "BLE GAP EVENT CONNECT %s", event->connect.status == 0 ? "OK!" : "FAILED!");
        if (event->connect.status == 0) {
            conn_id = event->connect.conn_handle;
            ESP_LOGI("BLE", "Connected! connection handle = %d", conn_id);
            xTaskCreate(send_keep_alive, "keep_alive_task", 4096, NULL, 5, NULL);
        }
        else {
            ble_app_advertise();
        }
        break;
    // Advertise again after completion of the event
    case BLE_GAP_EVENT_DISCONNECT:
        ESP_LOGI("GAP", "BLE GAP EVENT DISCONNECTED");
        conn_id = 1;  // reset connection ID
        // Reset global variables
        rpi_signal = -1;    
        user_distance = -1; 
        threshold_1 = -1;   // slower pattern 
        threshold_2 = -1;   // faster pattern
        if (event->connect.status != 0) {
            ble_app_advertise();
        }
        break;
    case BLE_GAP_EVENT_ADV_COMPLETE:
        ESP_LOGI("GAP", "BLE GAP EVENT");
        ble_app_advertise();
        break;
    default:
        break;
    }
    return 0;
}

// Define the BLE connection
void ble_app_advertise(void) {
    // GAP - device name definition
    struct ble_hs_adv_fields fields;
    const char *device_name;
    memset(&fields, 0, sizeof(fields));
    device_name = ble_svc_gap_device_name(); // Read the BLE device name
    fields.name = (uint8_t *)device_name;
    fields.name_len = strlen(device_name);
    fields.name_is_complete = 1;
    ble_gap_adv_set_fields(&fields);

    // GAP - device connectivity definition
    memset(&adv_params, 0, sizeof(adv_params));
    adv_params.conn_mode = BLE_GAP_CONN_MODE_UND; // connectable or non-connectable
    adv_params.disc_mode = BLE_GAP_DISC_MODE_GEN; // discoverable or non-discoverable
    // max and min commented out left to be asap
    //adv_params.itvl_min = (20 / 0.625); // 20 ms 
    //adv_params.itvl_max = (50 / 0.625); // 50 ms
    ble_gap_adv_start(ble_addr_type, NULL, BLE_HS_FOREVER, &adv_params, ble_gap_event, NULL);
    vTaskDelay(pdMS_TO_TICKS(1000));  // delay for 1 second to ensure advertising is active
    ESP_LOGI("BLE", "Advertising ...");
}

// The application
void ble_app_on_sync(void) {
    ble_hs_id_infer_auto(0, &ble_addr_type); // Determines the best address type automatically
    ble_app_advertise();                     // Define the BLE connection
}

// The infinite task
void host_task(void *param) {
    nimble_port_run(); // This function will return only when nimble_port_stop() is executed
}

void connect_ble(void) {
    nvs_flash_init();                          // 1 - Initialize NVS flash using
    // esp_nimble_hci_and_controller_init();   // 2 - Initialize ESP controller ** do this in menuconfig settings as outlined in README
    nimble_port_init();                        // 3 - Initialize the host stack
    ble_svc_gap_device_name_set(TAG); // 4 - Initialize NimBLE configuration - server name
    ble_svc_gap_init();                        // 4 - Initialize NimBLE configuration - gap service
    ble_svc_gatt_init();                       // 4 - Initialize NimBLE configuration - gatt service
    ble_gatts_count_cfg(gatt_svcs);            // 4 - Initialize NimBLE configuration - config gatt services
    ble_gatts_add_svcs(gatt_svcs);             // 4 - Initialize NimBLE configuration - queues gatt services.
    ble_hs_cfg.sync_cb = ble_app_on_sync;      // 5 - Initialize application
    nimble_port_freertos_init(host_task);      // 6 - Run the thread
}

 
void app_main() {
    int led_state;
    int led_pattern = -1;

    // configuration
    configure_led();
    connect_ble();

    while(1) {
        // Disconnected case, alert user with constant On 
        if (conn_id == 1) {
            if (led_pattern != 0) {
                printf("LED On, No connection alert\n");
                led_pattern = 0;
            }
            gpio_set_level(LED_GPIO, true);
            vTaskDelay(pdMS_TO_TICKS(100)); // 100 ms 
        }
        // Off case and slight delay to prevent useless/extremely close cycles and overuse of CPU
        else if (user_distance > threshold_1 || threshold_1 == -1 || user_distance == -1) {
            if (led_pattern != 1) {
                printf("LED Off\n");
                led_pattern = 1;
            }
            gpio_set_level(LED_GPIO, false);
            // Prevent CPU hogging between app main and interrupt task
            vTaskDelay(pdMS_TO_TICKS(50)); // 50 ms 
            //! can change to 10 for 10 ms if LED responsiveness is slow
        }
        // Fastest output case for within smallest threshold
        else if (user_distance <= threshold_2) {
            if (led_pattern != 2) {
                printf("Blink LED (Closer Threshold)\n");
                led_pattern = 2;
            }
            led_state = gpio_get_level(LED_GPIO);
            gpio_set_level(LED_GPIO, !led_state); // switch the LED state
            vTaskDelay((BLINK_PERIOD/4) / portTICK_PERIOD_MS); // wait 1/4 period
        }   
        // Slower output case for between largest and smallest threshold   
        else if (user_distance <= threshold_1) {
            if (led_pattern != 3) {
                printf("Blink LED (Further Threshold)\n");
                led_pattern = 3;
            }
            led_state = gpio_get_level(LED_GPIO);
            gpio_set_level(LED_GPIO, !led_state); // switch the LED state
            vTaskDelay(BLINK_PERIOD / portTICK_PERIOD_MS); // wait 1 period 
        }
    }
}
