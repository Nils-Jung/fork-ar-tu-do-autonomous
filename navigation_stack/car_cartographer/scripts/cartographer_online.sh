#!/bin/bash
#
#   Cartographer Online Script
#   Must be run in the ros.package directory
#

# Finds the first directory with a given name. Works upwards from the current directory until either a directory is found or "/" is reached
upfind() {
    local origindir=$PWD
    local found=false
    while [ true ]; do
        folder=$(find $PWD -type d -name $1 -maxdepth 1 -print -quit 2>/dev/null)
        if [ "$folder" != "" ]; then
            cd $origindir
            echo $folder
            exit 0
        elif [ "$PWD" = "/" ]; then
            cd $origindir
            echo ""
            exit 1
        fi
        cd ..
    done
}

filterstring="s/([[:cntrl:]]\[[0-9]{1,3}m)|(..;?)|//g"

scriptdir=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
logpath=$scriptdir/../files/cartographer.log

source $(upfind devel)/setup.bash

echo -n "Create .urdf file... " | tee $logpath
echo "" >> $logpath
xacro -o $scriptdir/../files/racer.urdf --inorder $(roscd racer_description && pwd)/urdf/racer.xacro 2>&1 | sed -r $filterstring >> $logpath
echo "Done." | tee -a $logpath

echo "Record topics & building map... " | tee -a $logpath
rosbag record -j -O $scriptdir/../files/map.bag scan imu tf __name:=rosbag_recording 2>&1 | sed -r $filterstring >> $logpath &
roslaunch car_cartographer cartographer_online.launch ros_version:=$ROS_DISTRO 2>&1 | sed -r $filterstring >> $logpath &
echo "Please drive with the car now (1.5 laps minimum, 3-5 laps recommended)."
read -p "Press RETURN to stop recording and finalize map."
rosservice call /finish_trajectory 0 2>&1 | sed -r $filterstring >> $logpath

if [ $ROS_DISTRO == "kinetic" ] ; then
    echo -n "Write map... " | tee -a $logpath
    rosservice call /write_assets "$scriptdir/../files/map" | sed -r $filterstring >> $logpath
    echo "Done." | tee -a $logpath
fi
if [ $ROS_DISTRO == "melodic" ] ; then
    echo -n "Write map stream... " | tee -a $logpath
    rosservice call /write_state "{filename: '$scriptdir/../files/map.bag.pbstream'}" | sed -r $filterstring >> $logpath
    echo "Done." | tee -a $logpath
fi

sleep 5

rosnode kill /rosbag_recording 2>&1 | sed -r $filterstring >> $logpath
rosnode kill /cartographer_node 2>&1 | sed -r $filterstring >> $logpath
rosnode kill /rviz_cartographer 2>&1 | sed -r $filterstring >> $logpath

if [ $ROS_DISTRO == "melodic" ] ; then
    echo -n "Write map... " | tee -a $logpath
    echo "" >> $logpath
    roslaunch car_cartographer cartographer_make_map.launch bag_filenames:=$scriptdir/../files/map.bag pose_graph_filename:=$scriptdir/../files/map.bag.pbstream 2>&1 | sed -r $filterstring >> $logpath
    echo "Done." | tee -a $logpath
fi
