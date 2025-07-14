f"cp -r ../proj_data/tile2net_export/dt_bk/{year}/tiles/static/nyc/256_19 data/test_runs/downtown_bk/imagery/raw_static/z19/2018"
f"cp -r ../proj_data/tile2net_export/dt_bk/{year}/tiles/{year}_256_19_info.* data/test_runs/downtown_bk/imagery/raw_static/z19/2018/."
f"cp -r ../proj_data/tile2net_export/dt_bk/{year}/tiles/dt_bk_{year}_256_info.json data/test_runs/downtown_bk/imagery/raw_static/z19/2006/2006_256_info.json"
f"cp -r ../proj_data/tile2net_export/dt_bk/{year}/tiles/dt_bk_2004_256_info.json data/test_runs/downtown_bk/imagery/raw_static/z19/2004/2004_256_info.json"

f"cp -r ../proj_data/tile2net_export/dt_bk/{year}/tiles/static/nyc/256_{z_level} data/test_runs/downtown_bk/imagery/raw_static/z{z_level}/{year}"
f"cp -r ../proj_data/tile2net_export/dt_bk/{year}/tiles/{original_name}_256_info.json data/test_runs/downtown_bk/imagery/raw_static/z{z_level}/{year}/{year}_256_info.json"
f"cp -r ../proj_data/tile2net_export/dt_bk/{year}/tiles/{original_name}_256_info.json data/test_runs/downtown_bk/imagery/raw_static/z{z_level}/{year}}/{year}_256_info.json"