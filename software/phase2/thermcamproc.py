from sharedcode import *
from senxor.mi48 import MI48, format_header, format_framestats
from senxor.utils import data_to_frame, remap, cv_filter,\
                         cv_render, RollingAverageFilter,\
                         connect_senxor

# threshold temperature degrees celsius
hazard_temp = 40

dminav = RollingAverageFilter(N=10)
dmaxav = RollingAverageFilter(N=10)

# set cv_filter parameters
par = {'blur_ks':3, 'd':5, 'sigmaColor': 27, 'sigmaSpace': 27}


def thermalcapture(picam_ready, thermal_ready, hazard_data):
    # Make an instance of the MI48, attaching USB for 
    # both control and data interface.
    mi48, connected_port, port_names = connect_senxor()

    # set desired FPS
    mi48.set_fps(20)

    # see if filtering is available in MI48 and set it up
    mi48.disable_filter(f1=True, f2=True, f3=True)
    mi48.set_filter_1(85)
    mi48.enable_filter(f1=True, f2=False, f3=False, f3_ks_5=False)
    mi48.set_offset_corr(0.0)

    mi48.set_sens_factor(100)
    mi48.get_sens_factor()

    # initiate continuous frame acquisition
    with_header = True
    mi48.start(stream=True, with_header=with_header)


    while True:
        try:
            # THERMAL STUFF
            local_ready = False
            # need to sync reading between processes
            # keep checking if both readys are true
            # print("checking if ready in thermal")
            while not local_ready:
                local_ready = (picam_ready.value == 1) and (thermal_ready.value == 1)

            # print(f"thermal capture time: {time.time()}")

            data, header = mi48.read()

            if data is None:
                # logger.critical('NONE data received instead of GFRA')
                print("NO DATA FROM THERMAL CAMERA")
                mi48.stop()

            #regular image
            min_temp = dminav(data.min())  # + 1.5
            max_temp = dmaxav(data.max())  # - 1.5
            frame = cv.flip(data_to_frame(data, (thermal_frame_x,thermal_frame_y), hflip=False),0)
            # frame2 = np.clip(frame, min_temp, max_temp)
            filt_uint8 = cv_filter(remap(frame), par, use_median=True,
                                use_bilat=True, use_nlm=False)
            
            # #hazard
            thresh = (hazard_temp-min_temp)/(max_temp-min_temp)*(255-min_temp)
            ret, thresh_image_hazard = cv.threshold(remap(frame), thresh, 255, cv.THRESH_BINARY)
            contours_hazard, ret = cv.findContours(thresh_image_hazard, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
            hazard_count = 0
            # Loop through the contours and filter based on area to detect the hand
            for contour in contours_hazard:
                area = cv.contourArea(contour)
                #print(f"Contour area: {area}")  # Debugging line
                # Filter out small contours that are likely noise
                if area > 1:
                    if hazard_count < max_hazards:
                        hazard_count += 1
                        hazard_data[hazard_count] = contour
                    # convex hull
                    hull = cv.convexHull(contour)
                    cv.drawContours(filt_uint8, [hull], -1, (255,255,0), 1)
                    # print("hazard detected")

            # print(hazards_contour_list)
            hazard_data[0] = hazard_count

            if GUI_THERMAL:
                cv_render(filt_uint8, colormap='rainbow2')
                key = cv.waitKey(1)  # & 0xFF
                if key == ord("q"):
                    break
            
            # make thermal ready false
            thermal_ready.value = 0

        except KeyboardInterrupt:
            break
    # close it once finished the while loop
    mi48.stop()
