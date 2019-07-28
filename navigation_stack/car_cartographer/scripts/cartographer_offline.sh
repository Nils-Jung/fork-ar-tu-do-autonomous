#!/bin/bash
#
#   Cartographer Offline Script
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

if [ $ROS_DISTRO == "kinetic" ] ; then
    echo -n "Create map... " | tee -a $logpath
    echo "" >> $logpath
    roslaunch car_cartographer cartographer_offline_fast.launch bag_filenames:=$1 ros_version:=$ROS_DISTRO 2>&1 | sed -r $filterstring >> $logpath
    echo "Done." | tee -a $logpath
fi

if [ $ROS_DISTRO == "melodic" ] ; then
    echo -n "Create map stream... " | tee -a $logpath
    echo "" >> $logpath
    roslaunch car_cartographer cartographer_offline_fast.launch bag_filenames:=$1 ros_version:=$ROS_DISTRO 2>&1 | sed -r $filterstring >> $logpath
    echo "Done." | tee -a $logpath

    echo -n "Create map... " | tee -a $logpath
    echo "" >> $logpath
    roslaunch car_cartographer cartographer_make_map.launch bag_filenames:=$1 pose_graph_filename:=$1.pbstream 2>&1 | sed -r $filterstring >> $logpath
    echo "Done." | tee -a $logpath
fi
