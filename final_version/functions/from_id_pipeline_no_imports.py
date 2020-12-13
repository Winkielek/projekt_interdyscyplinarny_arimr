import glob
import os
import shutil
import stat
import xml.etree.ElementTree as ET

import gdal
import pyproj
import requests


# A BTW WOLNE STRASZNIE DA SIĘ TO JAKOŚ PRZYŚPIESZYĆ UŻYWJAĆ SESIJ ALE TO TODO


def cord_reader(plot_ids_list: list):

    # Taking list contaings plots ID as strings
    # example ["260101_5.0037.569"]

    # Return dictionary with plots ID as key and
    # cords of plot as value

    # data check

    if (not isinstance(plot_ids_list, list)):
        raise Exception("List object is required")
    if (not isinstance(plot_ids_list[0], str)):
        raise Exception("List didnt contains only strings")

    list_of_cords = ["empty"] * len(plot_ids_list)
    iterator = 0
    s = requests.Session()
    for i in plot_ids_list:
        # ganerated with https://curl.trillworks.com/

        cookies = {
            '_ga': 'GA1.2.1313350324.1604560244',
            '_gid': 'GA1.2.1787115803.1607782926',
            'PHPSESSID': 'g8bs9k61ge3h2j3oqodpl1q5r6',
        }

        headers = {
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
            'Content-type': 'application/x-www-form-urlencoded',
            'Accept': '*/*',
            'Origin': 'https://polska.e-mapa.net',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://polska.e-mapa.net/',
            'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7',
        }

        data = {
            'action': 'wsporzedne_granic',
            'id_dzialki': i,
            'srid': '2180'
        }

        response = s.post('https://polska.e-mapa.net/application/modules/dzus/dzus.php', headers=headers,
                          cookies=cookies, data=data)

        out = response.text
        # OUT in form of string
        # Spliting and extracting cords
        out = out.split("'")
        out = out[1:len(out) - 1]
        final = []
        for i in out:
            if (i > "-"):
                final.append(i)

        list_of_cords[iterator] = final
        iterator = iterator + 1

    res = dict(zip(plot_ids_list, list_of_cords))

    return res


def converter(x_in, y_in):
    input_proj = pyproj.Proj(init='epsg:2180')
    output_proj = pyproj.Proj(init="epsg:4326")

    x_out, y_out = pyproj.transform(input_proj, output_proj, y_in, x_in)
    return (x_out, y_out)


def cut_plot(photo_path, XML_path, output_path, xmin, ymin, xmax, ymax):
    """
    photo_dir_path: sciezka do katalogu surowa_paczka.SAFE
    output_path: sciezka pliku wycietego zdjecia np.: zdjecie.png
    xmin, ymin, xmax, ymax: wspolrzedne prostokata do wyciecia
    """

    # XML part
    root = ET.parse(XML_path).getroot()
    epsg_info = list(list(root)[1])[0].find("HORIZONTAL_CS_CODE").text[5:]

    # photos_paths = os.listdir(photo_dir_path + "/GRANULE/" + target_dir + "/IMG_DATA/R10m")
    # for f in photos_paths:
    # if(f.find("TCI") != -1):
    #   photo_path = photo_dir_path + "/GRANULE/" + target_dir + "/IMG_DATA/R10m/" + f
    #  break

    # JP2 to TIFF
    gdal.Translate("temp_tiff.tiff", photo_path)

    # Wycinanie opcje
    opt = gdal.WarpOptions(srcSRS='epsg:' + epsg_info, dstSRS='epsg:4326',
                           outputBounds=(xmin, ymin, xmax, ymax), format="Gtiff")

    # Wycinanie
    res = gdal.Warp('usunac.tiff', 'temp_tiff.tiff', options=opt)

    # Wyciete do png
    gdal.Translate(output_path, res)

    # Usuwanie temp_tiff
    os.remove("temp_tiff.tiff")
    os.remove("usunac.tiff")
    os.remove(output_path + ".aux.xml")

    del res

    return

def rmtree(top):
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            filename = os.path.join(root, name)
            os.chmod(filename, stat.S_IWUSR)
            os.remove(filename)
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(top)

def filelOrg(MAIN_FOLDER_PATH):

        # MAIN_FOLDER_PATH = 'C:/Users/01121832/Documents/test' # MUST BE CHANGED directory of all data directories
    META_DATA_PATTERN = '/**/*TL.xml'
    IMG_DATA_PATTERN = '/**/*TCI.jp2'

    foldersList = os.listdir(MAIN_FOLDER_PATH)  # for loop

    for folder in foldersList:
        new_folder_path = MAIN_FOLDER_PATH + '/' + folder + '_extracted'
        os.mkdir(new_folder_path)

        meta_path = glob.glob(MAIN_FOLDER_PATH + '/' + folder + META_DATA_PATTERN, recursive=True)[0]
        shutil.move(meta_path, new_folder_path)

        img_path = glob.glob(MAIN_FOLDER_PATH + '/' + folder + IMG_DATA_PATTERN, recursive=True)[0]
        shutil.move(img_path, new_folder_path)

        rmtree(MAIN_FOLDER_PATH + '/' + folder)
    return


def download_data(latitude, longitude, date_from, date_to, folder_name, cloud_value: int, records_per_image: str = 1):
    os.system(
        'python ./CREODIAS_client/client.py -f -s Sentinel2 -l LEVEL1C -r 1 -c ' + str(cloud_value) + ' -p ' + str(
            longitude) + ',' + str(latitude) + ' -t ' + date_from + ' -e ' + date_to + ' -n ' + folder_name)
    return


def get_photo_from_id(id):
    id = str(id)
    cord_PUGW = cord_reader([id])[id]
    x_cords = []
    y_cords = []

    for i in cord_PUGW:
        cord_str = i.split(" ")
        x_temp = cord_str[0]
        y_temp = cord_str[1]

        x, y = converter(x_temp, y_temp)

        x_cords.append(float(x))
        y_cords.append(float(y))

    x_min = min(x_cords)
    x_max = max(x_cords)
    y_min = min(y_cords)
    y_max = max(y_cords)

    x_to_download = (x_min + x_max) / 2
    y_to_download = (y_min + y_max) / 2

    download_data(str(y_to_download), str(x_to_download), date_from="2020-05-01", date_to="2020-05-31", cloud_value=50,
                  folder_name="FOTO", records_per_image="1")

    # sciezka do poprawy
    photo_folder_path = 'download/' + os.listdir('download')[0]

    try:
        filelOrg(photo_folder_path)
    except:
        pass
    print('dupa')

    # sklejanie scieżki
    path_to_photos = "download/"
    for i in range(2):
        path_to_photos += str(os.listdir(path_to_photos)[0] + "/")

    for file_inside in os.listdir(path_to_photos):
        if "TCI" in file_inside:
            image_path = path_to_photos + file_inside
        if "MTD" in file_inside:
            XML_path = path_to_photos + file_inside

    print("dupa")

    cut_plot(image_path, XML_path, 'cuted_photo.jpg', x_min, y_min, x_max, y_max)

    rmtree("download/")

    return


get_photo_from_id("120906_2.0003.2761/2")
