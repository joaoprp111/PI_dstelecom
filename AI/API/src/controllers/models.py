from flask import Flask, send_file
from flask_restx import Api, Resource, reqparse
from werkzeug.datastructures import FileStorage
from PIL import Image
import json
import matplotlib.pyplot as plt
import math
import base64
from io import BytesIO

import torch
import torchvision
from torchvision.io import read_image 
from torchvision.utils import draw_bounding_boxes 
import torchvision.transforms as transforms

from src.server.instance import server
from src.database.db import db

app, api = server.app, server.api

models = db.getModels()
models_info = db.getModelsInfo()

parser = api.parser()
parser.add_argument('image', type=FileStorage, location='files', required=True)
parser.add_argument('step', type=int, required=True)
parser.add_argument('connector', type=int)

def box_center(box):

  xmin = box[0]
  ymin = box[1]
  xmax = box[2]
  ymax = box[3]

  center_x = (xmax - xmin) / 2
  center_y = (ymax - ymin) / 2

  return xmin + center_x, ymin + center_y

def getDropId(grid_box, values):
  count = 0
  min_id = None 
  min_diff = None

  while count < len(values):
    real_box = values[count]

    x_grid,y_grid = box_center(grid_box)
    x_real, y_real = box_center(real_box)

    diff = math.sqrt(((x_grid - x_real) * (x_grid - x_real)) + ((y_grid - y_real) * (y_grid - y_real)))

    if count == 0 or diff < min_diff:
      min_diff = diff
      min_id = count

    count += 1

  return min_id

def getConectorId(grid_box, values):
  count = 0
  min_id = None 
  min_diff = None

  while count < len(values):
    real_box = values[count]

    x_grid,y_grid = box_center(grid_box)
    x_real, y_real = box_center(real_box)

    diff = math.sqrt(((x_grid - x_real) * (x_grid - x_real)) + ((y_grid - y_real) * (y_grid - y_real)))

    if count == 0 or diff < min_diff:
      min_diff = diff
      min_id = count

    count += 1

  return min_id

def pil2datauri(img):
    #converts PIL image to datauri
    data = BytesIO()
    img.save(data, "JPEG")
    data64 = base64.b64encode(data.getvalue())
    return u'data:img/jpeg;base64,'+data64.decode('utf-8')

@api.route('/detect')
class ObjectDetection(Resource):
    def get(self,):
        return models_info

    @api.expect(parser)
    def post(self,): 
        args = parser.parse_args()
        print(f'Args: {args}')
        uploaded_file = args['image']  # This is FileStorage instance
        step = args['step']
        connector = args['connector']
        print('Step: ',step)
        print('Connector: ',connector) 

        connector = 3

        if step == None:
          return {'message': 'Erro ao reconhecer o passo do trabalho.'}, 500

        else:
            print(f'Uploaded file: {uploaded_file}')

            img = Image.open(uploaded_file)
            original_size = img.size
            img = img.resize((640,640))

            if step == 1:
              models = [0, 3]
              # 1. Verificar se o PDO está aberto com o modelo de Object Detection 
              # Se não reconhecer um PDO aberto apontamos essa falha no relatório final
              print('Modelo com id == 0')
              model = models[models[0]]
              results = model(img)
              outputs = results.pandas().xyxy[0]
              outputs['class'] = outputs.index
              labels = outputs[['class','name']]
              outputs_json = labels.to_json(orient='records')
              print('Outputs do passo 1 (verificar se o estado do PDO):', outputs_json)

              # 2. Tentamos verificar a referência do PDO
              # Se falhar também incluimos a falha no relatório final

              return outputs_json, 200

            elif step == 9:
                model = models[1]
                results = model(img)
                outputs = results.pandas().xyxy[0]

                outputs.drop(outputs[outputs['confidence'] < 0.5].index, inplace=True)
                values = outputs.values
                print(values[:3])

                #Open grid
                f = open('static/grids/Conectores/grid_conectors_esquerda_pra_direita.json')
                grid = json.load(f)

                #Get ref box
                grid_box = grid['grid'][connector-1]
                label = grid_box['label']
                grid_box = [grid_box['xmin'], grid_box['ymin'], grid_box['xmax'], grid_box['ymax']]

                #Get id
                id_escolhido = getConectorId(grid_box,values)

                #Identificar na imagem
                transform = transforms.Compose([
                  transforms.PILToTensor()
                ])
                img = transform(img)
                boxes = []
                #labels = []
                colors = []

                if len(values) > 0:
                  row = values[id_escolhido]

                  xmin = row[0]
                  ymin = row[1]
                  xmax = row[2] 
                  ymax = row[3] 

                  #labels.append(label)

                  box = [xmin, ymin, xmax, ymax]
                  boxes.append(box)

                  color = 'red' if label == 'ConectorOcupado' else 'green' if 'ConectorLivre' else 'blue'
                  colors.append(color)
                  
                  boxes = torch.tensor(boxes, dtype=torch.float)

                  '''img = draw_bounding_boxes(img,
                                          boxes=boxes,
                                          labels=labels,
                                          colors=colors,
                                          width=2)'''

                  img = draw_bounding_boxes(img,
                                          boxes=boxes,
                                          colors=colors,
                                          width=2)

                  img = torchvision.transforms.ToPILImage()(img)
                  img = img.resize(original_size)

                  img_uri = pil2datauri(img)

                  print('imagem detetada')
                  #print('image uri: ', img_uri)
                  outputs_json = {'image': {
                    'uri': img_uri,
                    'type': 'image/jpeg',
                    'name': 'image.jpeg'
                  }}

                else:
                  outputs_json = {'message' : 'O resultado da deteção não teve sucesso!'}
                 
                print('modelo com id == 1')

            return outputs_json, 200