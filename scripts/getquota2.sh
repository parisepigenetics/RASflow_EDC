
gid=$(getent group $1 | cut -f 3 -d ':')
tot=$(lfs quota -h -p $gid /shared/projects/$1 | awk '{print $2}' | awk 'NR==4{ print; }')
extra=$(lfs quota -h -p $gid /shared/projects/$1 | awk '{print $3}' | awk 'NR==4{ print; }')
used=$(lfs quota -h -p $gid /shared/projects/$1 | awk '{print $1}' | awk 'NR==4{ print; }')

echo $tot $extra $used

