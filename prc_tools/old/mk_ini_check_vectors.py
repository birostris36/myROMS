# -*- coding: utf-8 -*-
"""
Created on Thu Nov 14 09:44:00 2024

@author: shjo
"""

PKG_path = 'D:/shjo/projects/myROMS/prc_tools/' # Location of JNUROMS directory
import sys 
sys.path.append(PKG_path)
import utils.ROMS_utils01 as ru
import utils.ROMS_utils02 as ru2
from utils.ncCreate import create_ini
import matplotlib.pyplot as plt
import numpy as np
import datetime as dt
from tqdm import tqdm
from scipy.interpolate import griddata
from netCDF4 import Dataset,date2num,num2date
import matplotlib.path as mpath
import cartopy
import cartopy.crs as ccrs
import cartopy.feature as cf
from mpl_toolkits.axes_grid1 import make_axes_locatable
import numpy as np
from scipy.interpolate import interp2d, griddata
#== Define Inputs files =======================================================
My_Ini='D:/shjo/projects/myROMS/outputs/test_ini.nc' # Initial file name (to create)
My_Grd='D:/shjo/projects/myROMS/test_data/Domain.nc' # Grd name

#-- Define OGCM path ----------------------------------------------------------
ncdir='D:/shjo/projects/myROMS/test_data/raw/'
sshNC=ncdir+'HYCOM_GLBy0.08_ssh_2019_121.nc'
tempNC=ncdir+'HYCOM_GLBy0.08_temp_2019_121.nc'
saltNC=ncdir+'HYCOM_GLBy0.08_salt_2019_121.nc'
uNC=ncdir+'HYCOM_GLBy0.08_u_2019_121.nc'
vNC=ncdir+'HYCOM_GLBy0.08_v_2019_121.nc'

#-- Define Parameters ---------------------------------------------------------
Ini_title='my Test swan' # title for NC description

print('!!!!!!!!!!!!!!!!!!!!!!\n레이어 개수 스트레팅 nc에서 읽어오는걸로 변결해야함\n 데이터 잘 들어갔는지 마지막으로 확인!!!!')
MyVar={'Layer_N':50,'Vtransform':2,'Vstretching':4,\
       'Theta_s':7,'Theta_b':.1,'Tcline':450,'hmin':50}
conserv=1
# OGCM Variables name
OGCMVar={'lon_rho':'lon','lat_rho':'lat','depth':'z','time':'ocean_time',\
         'lon_u':'lon','lat_u':'lon','lon_v':'lon','lat_v':'lat',
         'temp':'temp','salt':'salt','u':'u','v':'v','zeta':'ssh'}

# Define time info
t_rng=['2019-05-01','2019-05-01'] # Inital time 
My_time_ref='days since 1990-1-1 00:00:00' # time ref

#== Starts Calc ===============================================================

#-- Get My Grid info ----------------------------------------------------------
ncG=Dataset(My_Grd)
lonG,latG=ncG['lon_rho'][:],ncG['lat_rho'][:]
angle,topo,mask=ncG['angle'][:],ncG['h'][:],ncG['mask_rho'][:]
ncG.close()

atG,onG=lonG.shape
cosa,sina=np.cos(angle),np.sin(angle)

#-- Get OGCM Grid info --------------------------------------------------------
ncO=Dataset(tempNC)
lonO,latO=ncO[OGCMVar['lon_rho']][:],ncO[OGCMVar['lat_rho']][:];
depthO=ncO[OGCMVar['depth']][:]
ncO.close()

#-- Get OGCM lon lat coordinates for slicing ----------------------------------

lonO_co01=np.where( (lonO[0,:]>=np.min(lonG)) & (lonO[0,:]<=np.max(lonG)) )[0]
latO_co01=np.where( (latO[:,0]>=np.min(latG)) & (latO[:,0]<=np.max(latG)) )[0]

latO_re=latO[latO_co01,0]
lonO_re=lonO[0,lonO_co01]

lonGmax=np.max(np.abs(np.diff(lonG[0,:])))
latGmax=np.max(np.abs(np.diff(latG[:,0])))

lonOmax=np.max(np.abs(np.diff(lonO_re[:])))
latOmax=np.max(np.abs(np.diff(latO_re[:])))

lonEval=np.max([ np.max(lonO_re) ,np.max(lonG)+lonOmax])
lonSval=np.min([ np.min(lonO_re), np.min(lonG)-lonOmax])

latEval=np.max([ np.max(latO_re),np.max(latG)+latOmax])
latSval=np.min([ np.min(latO_re),np.min(latG)-latOmax])

lonO_co=np.where((lonO[0,:]>=lonSval)&(lonO[0,:]<=lonEval))[0]
latO_co=np.where((latO[:,0]>=latSval)&(latO[:,0]<=latEval))[0]

latO_s=latO[latO_co,0]
lonO_s=lonO[0,lonO_co]

lonO_s_m,latO_s_m=np.meshgrid(lonO_s,latO_s)


#-- Process Times--------------------------------------------------------------
OGCM_TIMES=Dataset(sshNC)[OGCMVar['time']]
TIME_UNIT=OGCM_TIMES.units
OGCM_times=num2date(OGCM_TIMES[:],TIME_UNIT)
Tst=dt.datetime(int(t_rng[0].split('-')[0]), int(t_rng[0].split('-')[1]),int(t_rng[0].split('-')[2]),0)
Ted=dt.datetime(int(t_rng[1].split('-')[0]), int(t_rng[1].split('-')[1]),int(t_rng[1].split('-')[2]),23)
TIMES_co=np.where( (OGCM_times>=Tst)&(OGCM_times<=Ted) )[0]
tmp_y,tmp_m,tmp_d=int(t_rng[0].split('-')[0]),int(t_rng[0].split('-')[1]),int(t_rng[1].split('-')[-1])
tmp_dif=date2num(dt.datetime(tmp_y,tmp_m,tmp_d),TIME_UNIT)-date2num(dt.datetime(tmp_y,tmp_m,tmp_d),My_time_ref)
Ini_time_num=((date2num(dt.datetime(tmp_y,tmp_m,1),TIME_UNIT)-tmp_dif))*86400
# print('!!! Ini_time + 16d !!!')

#-- Create a dump ncfile ------------------------------------------------------
create_ini(My_Ini,mask,topo,MyVar,Ini_time_num,Ini_title,ncFormat='NETCDF4')

#-- Get OGCM data for initial -------------------------------------------------
OGCM_Data={}#,OGCM_Mask={}
#for i in ['u','v','temp','salt','zeta','ubar','vbar']:
for i in ['u','v']:

    print('!!! Data processing : '+i+' !!!')
    if i == 'zeta':
        tmp_data=np.squeeze(Dataset(sshNC)[OGCMVar[i]][TIMES_co,latO_co,lonO_co])
        tmp_mask=np.invert(tmp_data.mask)
    elif i=='ubar':
        tmp_u=np.squeeze(Dataset(uNC)[OGCMVar['u']][TIMES_co,:,latO_co,lonO_co])
        tmp_mask_=np.invert(tmp_u.mask)[:,:,:]
        
        tmp_u[tmp_u.mask]=0
        
        du=np.zeros([tmp_u.shape[1],tmp_u.shape[2]])
        zu=np.zeros_like(du)
        dz=np.gradient(-depthO)
        for n in range(len(depthO)):
            du=du+dz[n]*tmp_u[n,:,:].data
            zu=zu+dz[n]*tmp_mask_[n,:,:]
        DATA=du/zu
        # DATA[DATA==0]=np.nan
        tmp_mask=tmp_mask_[0,:,:]
        tmp_data=DATA
        
    elif i=='vbar':
        tmp_v=np.squeeze(Dataset(vNC)[OGCMVar['v']][TIMES_co,:,latO_co,lonO_co])
        tmp_mask_=np.invert(tmp_v.mask)[:,:,:]
        
        tmp_v[tmp_v.mask]=0
        
        dv=np.zeros([tmp_v.shape[1],tmp_v.shape[2]])
        zv=np.zeros_like(dv)
        dz=np.gradient(-depthO)
        for n in range(len(depthO)):
            dv=dv+dz[n]*tmp_v[n,:,:].data
            zv=zv+dz[n]*tmp_mask_[n,:,:]
        DATA=dv/zv
        # DATA[DATA==0]=np.nan
        tmp_mask=tmp_mask_[0,:,:]
        tmp_data=DATA

    else:
        if i=='u' :
            OGCM_npth=uNC;
        elif i=='v':
            OGCM_npth=vNC;
        elif i=='temp':
            OGCM_npth=tempNC;
        elif i=='salt':
            OGCM_npth=saltNC;
       
        tmp_data=np.squeeze(Dataset(OGCM_npth)[OGCMVar[i]][TIMES_co,:,latO_co,lonO_co])
        tmp_mask=np.invert(tmp_data.mask)
    ## Another way to create mask
    # mv=ncO[OGCMVar[i]].missing_value
    if len(tmp_data.shape)==2:

        data=griddata((lonO_s_m[tmp_mask].flatten(),latO_s_m[tmp_mask].flatten()),\
                      tmp_data[tmp_mask].flatten(),(lonO_s_m.flatten(),latO_s_m.flatten()),'nearest')
        data_ex=data.reshape(latO_s_m.shape)
        data=griddata((lonO_s_m.flatten(),latO_s_m.flatten()),\
                      data_ex.flatten(),(lonG.flatten(),latG.flatten()),'cubic')
        data=data.reshape(lonG.shape)
        tmp_var=data
        if np.sum(np.isnan(data))!=0:
            tmp_var[np.isnan(tmp_var)]=np.nanmean(tmp_var)
            data=tmp_var 
       
    elif len(tmp_data.shape)==3:
    
        data,n=np.zeros([len(depthO),atG,onG]),0
        for j,k in tqdm(zip(tmp_data,tmp_mask)):
     
            data_=griddata((lonO_s_m[k].flatten(),latO_s_m[k].flatten()),\
                          j[k].flatten(),(lonO_s_m.flatten(),latO_s_m.flatten()),'nearest')
            data_ex=data_.reshape(latO_s_m.shape)
            data_=griddata((lonO_s_m.flatten(),latO_s_m.flatten()),\
                          data_ex.flatten(),(lonG.flatten(),latG.flatten()),'cubic')
            data[n]=data_.reshape(latG.shape)
            
        ### Add 20250320
            tmp_var=data[n]
            if np.sum(~np.isnan(data[n]))==0:
                data[n]=data[n-1]

            if np.sum(np.isnan(data[n]))!=0:
                tmp_var[np.isnan(tmp_var)]=np.nanmean(tmp_var)
                data[n]=tmp_var
            n+=1
    OGCM_Data[i]=data
    
    
    
u=OGCM_Data['u']*cosa+OGCM_Data['v']*sina
v=OGCM_Data['v']*cosa-OGCM_Data['u']*sina
    
tmp_u=u[10]
tmp_v=v[10]

u_geo = tmp_u * np.cos(angle) - tmp_v * np.sin(angle)
v_geo = tmp_u * np.sin(angle) + tmp_v * np.cos(angle)
tmp_u=u_geo
tmp_v=v_geo

n=2;Label_size=14

PC = ccrs.PlateCarree(central_longitude=0.0,globe=None)

PC180 = ccrs.PlateCarree(central_longitude=200.0,globe=None)
fig, ax = plt.subplots(1, 1, figsize=(6,8),
                    subplot_kw={'projection': PC180},dpi=200,constrained_layout=True)
gl = ax.gridlines(crs=PC, draw_labels=True,y_inline=False,x_inline=False,
                    linewidth=.6, color='k', alpha=0.45, linestyle='-.',\
                        xlocs=range(-180, 180, 2),ylocs=range(30, 90, 2),zorder=200)
gl.xlabels_top,gl.ylabels_right = False,False
gl.top_labels=False   # suppress top labels
gl.right_labels=False # suppress right labels
n=1
gl.xlabel_style = gl.ylabel_style = {"size" : 14}
ax.add_feature(cf.COASTLINE.with_scale("110m"), lw=1,zorder=110)
ax.add_feature(cf.LAND,color=[.75,.75,.75],zorder=100)
ax.set_title('Surface uv',loc='right',fontdict={'fontsize':Label_size+3,'fontweight':'regular'})
q1 = ax.quiver(lonG[::n,::n],latG[::n,::n],tmp_u[::n,::n],tmp_v[::n,::n],
    scale=4.,headwidth=8.,headaxislength=10,headlength=13,color='k',
    minlength=1,edgecolor='k',minshaft=1.3,alpha=1.,transform=ccrs.PlateCarree(),zorder=100,
    pivot='mid',angles='xy')
#qk = ax.quiverkey(q1, 0.23, .85, 1., r'$1 m^2/s $', labelpos='E',color='k',
#                coordinates='figure')
#M=plt.contourf(lonG,latG,v_rho,cmap=GSMCMAP,levels=GSM_Levels,transform=PC,zorder=1)
#plt.contour(lon_new_m,lat_new_m,DATA_rgd_mean,colors='k',zorder=100,transform=PC,linestyles='dashdot')
# M=plt.pcolor(lon_m,lat_m,mydataD,cmap=Mycmap,vmin=-.5,vmax=.5,transform=ccrs.PlateCarree())
ax.set_extent([127.3, 135, 34.5, 41.5], crs=PC)
#ax.tick_params(axis='both', which='major', labelsize=Label_size)
#divider = make_axes_locatable(ax)
#ax_cb = divider.new_horizontal(size="5%", pad=.1, axes_class=plt.Axes)
#fig.add_axes(ax_cb)
# cb=plt.colorbar(M,extend='both',pad=0.01,cax=ax_cb,ticks=CTicks)
#cb=plt.colorbar(M,extend='both',pad=0.01,cax=ax_cb,ticks=Cticks)

if 0:
    plt.savefig(snm+'_eof',bbox_inches='tight')
plt.show()

    
    
    
    
  
    
#-- Process vector elements ---------------------------------------------------
u=ru2.rho2u_3d(OGCM_Data['u']*cosa+OGCM_Data['v']*sina)
v=ru2.rho2v_3d(OGCM_Data['v']*cosa-OGCM_Data['u']*sina)

ubar=ru2.rho2u_2d(OGCM_Data['ubar']*cosa+OGCM_Data['vbar']*sina)
vbar=ru2.rho2v_2d(OGCM_Data['vbar']*cosa-OGCM_Data['ubar']*sina)



'''

salt=np.squeeze(Dataset(saltNC)[OGCMVar['salt']][TIMES_co,:,latO_co,lonO_co])
tmp_mask=np.invert(salt.mask)
salt.data[-3]

plt.pcolor(OGCM_Data['temp'][-1])

print(np.)

'''


#-- Process ROMS Vertical grid ------------------------------------------------
Z=np.zeros(len(depthO)+2)
Z[0]=100;Z[1:-1]=-depthO;Z[-1]=-100000

Rzeta=OGCM_Data['zeta']
zr=ru.zlevs(MyVar['Vtransform'],MyVar['Vstretching'],MyVar['Theta_s'],\
         MyVar['Theta_b'],MyVar['Tcline'],MyVar['Layer_N'],\
             1,topo,Rzeta);
zu=ru2.rho2u_3d(zr);
zv=ru2.rho2v_3d(zr);
zw=ru.zlevs(MyVar['Vtransform'],MyVar['Vstretching'],MyVar['Theta_s'],\
         MyVar['Theta_b'],MyVar['Tcline'],MyVar['Layer_N'],\
             5,topo,Rzeta);
dzr=zw[1:,:,:]-zw[:-1,:,:]
dzu=ru2.rho2u_3d(dzr);
dzv=ru2.rho2v_3d(dzr);

#-- Add a level on top and bottom with no-gradient ----------------------------
temp,salt=OGCM_Data['temp'],OGCM_Data['salt']

u1=np.vstack((np.expand_dims(u[0,:,:],axis=0)\
              ,u,np.expand_dims(u[-1,:,:],axis=0)))
v1=np.vstack((np.expand_dims(v[0,:,:],axis=0)\
              ,v,np.expand_dims(v[-1,:,:],axis=0)))
temp=np.vstack((np.expand_dims(temp[0,:,:],axis=0)\
              ,temp,np.expand_dims(temp[-1,:,:],axis=0)))
salt=np.vstack((np.expand_dims(salt[0,:,:],axis=0)\
              ,salt,np.expand_dims(salt[-1,:,:],axis=0)))
    
#-- Transform z-coordinate to sigma-coordinates -------------------------------
print('!!! Transformming z --> sigma... !!!')
u=ru.ztosigma(np.flip(u1,axis=0),zu,np.flipud(Z));
v=ru.ztosigma(np.flip(v1,axis=0),zv,np.flipud(Z));
temp=ru.ztosigma(np.flip(temp,axis=0),zr,np.flipud(Z));
salt=ru.ztosigma(np.flip(salt,axis=0),zr,np.flipud(Z));

#-- Volume conservation -------------------------------------------------------
if conserv==1:
    u = u - np.sum(u*dzu,axis=0)/np.sum(dzu,axis=0) + ubar
    v = v - np.sum(v*dzv,axis=0)/np.sum(dzv,axis=0) + vbar   
    
#-- Calc Barotropic velocities2 -----------------------------------------------
ubar_=np.sum(u*dzu,axis=0)/np.sum(dzu,axis=0)
vbar_=np.sum(v*dzv,axis=0)/np.sum(dzv,axis=0)

ncI=Dataset(My_Ini,mode='a')
ncI['zeta'][:]=Rzeta
# ncI['SSH'][:]=Rzeta
ncI['temp'][:]=temp
ncI['salt'][:]=salt
ncI['u'][:]=u
ncI['v'][:]=v
ncI['ubar'][:]=ubar_
ncI['vbar'][:]=vbar_
ncI.close()







