#_____________________________________________________________________________________________________#

######## 01 - Importar Módulos necessários
#_____________________________________________________________________________________________________#

import arcpy
import math
from arcpy import env
from arcpy.sa import *

#_____________________________________________________________________________________________________#

######## 02 - Informar dados de entrada estão salvos
#_____________________________________________________________________________________________________#

#Pasta onde estão os rasters a serem incluídos na análise multivariada
input_folder = "D:/ZONAS_MANEJO"
​
#Endereço do shapefile que será usado como mascara 
shp_mask = "D:/ZONAS_MANEJO/SHP/area.shp"
​
#Quantidade de Componentes Princpipais a serem selecionadas 
num_of_PCs = 3
​
#Quantidade de clusters a serem criados na análise multivariada.
#Se o valor for igual a 0, o ArcGIS define a quantidade de grupos em função da pseudo estatistica F.
num_of_clusters = 0
​
#Define o método de clusterização as ser utilizado
# k-médias (metodo = 1) ou k-medoides (metodo = 2) 
metodo = 2
​
#Area mínima (em hectares) da ZM
area_min = 1.0

#_____________________________________________________________________________________________________#

######## 03 - Cria pastas onde os resultados serão salvos
#_____________________________________________________________________________________________________#

#Cria pasta de resultados
arcpy.CreateFolder_management(input_folder,"RESULTADOS")
​
#Limpa pasta temporaria
arcpy.Delete_management("in_memory")

#_____________________________________________________________________________________________________#

######## 04 - Inicia processo de recorte, padronização e redimensinamento dos rasters de entrada
#_____________________________________________________________________________________________________#

arcpy.env.overwriteOutput = True
arcpy.env.workspace = input_folder
for raster_file in arcpy.ListFiles("*.TIF"):
    raster_file_mskd = ExtractByMask(raster_file, shp_mask)
    arcpy.CalculateStatistics_management (raster_file_mskd)
    rst = arcpy.Raster(raster_file_mskd)
    rst_avg = rst.mean
    rst_sd = rst.standardDeviation
    standarized = ((rst-rst_avg)/rst_sd)
    standarized_min = standarized.minimum
    standarized_max = standarized.maximum
    standarized_scaled = ((standarized - standarized.minimum) * (255-0) / 
                          (standarized.maximum - standarized.minimum)) + 0
    part = raster_file.split('.')[0]
    out_raster = "in_memory\\" + part + '_norm.tif'
    standarized_scaled.save(out_raster)     

#_____________________________________________________________________________________________________#

######## 05 - Realiza Análise de Componentes Principais (ACP)
#_____________________________________________________________________________________________________#

#conta a quantidade de rasters dentro do diretório temporario
arcpy.env.workspace = "in_memory\\"
raster_list = arcpy.ListRasters("*", "TIF")
rst_count = len(raster_list)
​
#Cria lista contendo o nome das bandas slecionadas em função da quantidade de CPS selecionados.
PC_list = []
if num_of_PCs <= rst_count:
    PC_list.extend(range(1, num_of_PCs+1))
else:
    PC_list.extend(range(1, rst_count+1))   
​
#Executa Analise de Componentes Principais e exporta relatório
PC_raster = PrincipalComponents(raster_list, rst_count,input_folder  + "/RESULTADOS/ACP_report.txt")
​
#Cria raster com as bandas selecionadas
PC_raster_selected = arcpy.ia.ExtractBand(PC_raster, PC_list)
​
#Cria shapefile de pontos contendo os valores de cada banda em um campo separado
raster_points = "in_memory\\ACP_pts"
arcpy.RasterToPoint_conversion(PC_raster_selected, raster_points, "VALUE")
arcpy.management.DeleteField(raster_points, "grid_code")
ExtractMultiValuesToPoints(raster_points,PC_raster_selected, "NONE")

#_____________________________________________________________________________________________________#

######## 06 - Realiza a Analise de Agrupamentos (Clusterização) nos pontos resultantes da ACP
#_____________________________________________________________________________________________________#

#Define a feature class criada com as informações de clusterização
clustered_points = "in_memory\clustered_pts"
​
#Cria lista com o nome dos campos que serão utilizados na clusterização
fields = arcpy.ListFields(raster_points,"b*")
field_list = []
for field in fields:
    field_list.append(field.name)
​
## Análise de Agrupamento (Clusterização) ##
​
#Define o algoritmo de agrupamento
if metodo == 1:
    metodo_selecionado = "K_MEANS"
else:
    metodo_selecionado = "K_MEDOIDS"
​
#Execução clusterização sem definição de numero de grupos
if num_of_clusters == 0:
    arcpy.MultivariateClustering_stats(raster_points,clustered_points,field_list,
                                       metodo_selecionado,"OPTIMIZED_SEED_LOCATIONS",
                                       None,"","in_memory\pseudo_F_statistics")
    wkspc = arcpy.env.workspace = "in_memory\\"
    tables = arcpy.ListTables('*pseudo_F_statistics')
    for table in tables:
        out_svg = wkspc + "pseudo_F_statistics.svg"
        chart = arcpy.Chart("Grafico_01")
        chart.title = "Otimização de Quantidade de Clusters"
        chart.type = "line"
        chart.xAxis.field = "NUM_GROUPS"
        chart.yAxis.field = "PSEUDO_F"
        chart.xAxis.title = "Qtde. de Clusters"
        chart.yAxis.title = "Pseudo F Statistics"
        chart.dataSource = table
        chart.exportToSVG(input_folder + "/RESULTADOS/grafico.svg", width=500, height=400)
​
#Execução com número de grupos definido
else:
    arcpy.MultivariateClustering_stats(raster_points,clustered_points,field_list,
                                       metodo_selecionado,"OPTIMIZED_SEED_LOCATIONS",
                                       None,num_of_clusters)  
​#_____________________________________________________________________________________________________#

######## 07 - Converte os resultados da clusterização em poligonos
#_____________________________________________________________________________________________________#

#Define a resolução espaciaL do raster de ZMs
rst_cellsize = arcpy.GetRasterProperties_management(PC_raster_selected, "CELLSIZEX").getOutput(0)
​
#Converte pontos resuLtantes do cLusterizacdo em raster
arcpy.PointToRaster_conversion(clustered_points, "CLUSTER_ID", "in_memory\Zonas_Manejo_rst","","", rst_cellsize)
​
#Converte raster em poligonos 
arcpy.conversion.RasterToPolygon("in_memory\Zonas_Manejo_rst","in_memory\Zonas_Manejo_fc", 
                                 "NO_SIMPLIFY","","SINGLE_OUTER_PART","")
​
#Adiciona campo e calcula area geodésica dos poligonos
arcpy.management.AddField("in_memory\Zonas_Manejo_fc", "AREA", "DOUBLE") 
arcpy.CalculateField_management("in_memory\Zonas_Manejo_fc", "AREA","!shape.geodesicArea@hectares!","PYTHON3")
​
#Loop para eLiminar poLígonos menores que a area minima 
arcpy.MakeFeatureLayer_management("in_memory\Zonas_Manejo_fc", "ZM") 
arcpy.SelectLayerByAttribute_management("ZM", "NEW_SELECTION",'"AREA" < 1.0') 
arcpy.Eliminate_management("ZM", "in_memory\ZM_E0","AREA")
​
cursor = arcpy.da.SearchCursor("in_memory\ZM_E0", "AREA")
first_rec = True
for row in cursor:
    if first_rec:
        first_rec = False
        min_value = float(row[0])
    else:
        min_value = min(float(row[0]),min_value)
i = 0
while min_value <= area_min:
    arcpy.MakeFeatureLayer_management("in_memory\ZM_E" + str(i), "ZM" + str(i))
    arcpy.SelectLayerByAttribute_management("ZM" + str(i), "NEW_SELECTION",'"AREA" <' + str(area_min)) 
    arcpy.Eliminate_management("ZM" + str(i), "in_memory\ZM_E" + str(i+1),"AREA") 
    arcpy.CalculateField_management("in_memory\ZME"+ str(i+1),"AREA","!shape.geodesicArea@hectares!","PYTHON3")
    
    cursor = arcpy.da.SearchCursor("in_memory\ZME"+ str(i+1),"AREA")
    first_rec = True
    for row in cursor:
        if first_rec:
            first_rec = False
            min_value = float(row[0])
        else:
            min_value = min(float(row[0]),min_value)
    i = i + 1
​
#Cria shapefiLe das Zonas de Manejo
arcpy.management.CopyFeatures("in_memory\ZM_E" + str(i), input_folder + "/RESULTADOS/ZM2.shp")
arcpy.Delete_management("in_memory")
globals().clear()
