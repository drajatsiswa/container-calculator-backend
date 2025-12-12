from flask import Flask, request, jsonify
from flask_cors import CORS
from py3dbp import Packer, Bin, Item

app = Flask(__name__)
CORS(app)  # Izinkan semua domain (Hostinger, localhost, dll)

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.get_json()
    container = data['container']
    boxes = data['boxes']
    settings = data['settings']

    # Hitung total volume & berat
    total_cbm = sum(b['volume_m3'] * b['qty'] for b in boxes)
    total_weight = sum(b['weight'] * b['qty'] for b in boxes)
    container_volume = (container['length_cm'] * container['width_cm'] * container['height_cm']) / 1_000_000
    max_usable = container_volume * settings['volumeThreshold']

    # Packing dengan py3dbp (cepat & akurat)
    packer = Packer()
    packer.add_bin(Bin(
        container['name'],
        container['width_cm'],
        container['height_cm'],
        container['length_cm'],
        container['maxWeight']
    ))

    for box in boxes:
        for _ in range(box['qty']):
            packer.add_item(Item(
                box['name'],
                box['l'], box['t'], box['p'],  # width, height, depth
                box['weight']
            ))

    packer.pack(bigger_first=True, distribute_items=True)

    # Proses hasil
    placed_items = []
    box_counts = {}
    placed_boxes = 0
    placed_volume = 0

    if packer.bins:
        for item in packer.bins[0].items:
            placed_items.append({
                'name': item.name,
                'position': item.position,
                'rotation': item.rotation,
                'dim': item.get_dimension()
            })
            box_counts[item.name] = box_counts.get(item.name, 0) + 1
            placed_boxes += 1
            placed_volume += (item.width * item.height * item.depth) / 1_000_000

    visual_percent = (placed_volume / container_volume) * 100 if container_volume > 0 else 0

    result_data = {
        'totalCBM': round(total_cbm, 3),
        'totalWeight': int(total_weight),
        'containerVolume': round(container_volume, 3),
        'maxUsableVolume': round(max_usable, 3),
        'usableVolumePercent': round((total_cbm / max_usable) * 100, 1) if max_usable > 0 else 0,
        'weightPercent': round((total_weight / container['maxWeight']) * 100, 1),
        'isLoadable': total_cbm <= max_usable and total_weight <= container['maxWeight'],
        'boxes': boxes
    }

    packing_result = {
        'placedItems': placed_items,
        'placedBoxes': placed_boxes,
        'totalBoxes': sum(b['qty'] for b in boxes),
        'visualVolumePercent': round(visual_percent, 1),
        'boxCounts': box_counts,
        'algorithm': 'py3dbp + Flask'
    }

    return jsonify({
        'resultData': result_data,
        'packingResult': packing_result
    })

if __name__ == '__main__':
    app.run(debug=True)
