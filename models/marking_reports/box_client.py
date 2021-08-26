import box_files

# create and cache an instance of the BOX connection and download tokens 
# and make them accessible from current so it can be used in modules

box_client = cache.ram('box_client',
                       lambda: box_files.authorize_jwt_client_json(),
                       time_expire=3600)

current.box_client = box_client

# create and cache a downscoped token to use in providing download links for audio files
# The expiry time is a bit of guess - they seem to last an hour or so but not precisely.
# Can we use the dl_token.expires_in to set a real expiry time?

dl_token = cache.ram('dl_token',
                     lambda: box_files.downscope_to_root_download(),
                     time_expire=3600)

current.dl_token = dl_token

