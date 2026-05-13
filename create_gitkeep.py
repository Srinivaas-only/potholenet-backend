import os
base = r'c:\Users\User\OneDrive\Documents\Pothole Detection\potholenet-backend'
paths = [
    os.path.join(base, 'app', 'ml_models', '.gitkeep'),
    os.path.join(base, 'retraining_queue', '.gitkeep'),
]
for p in paths:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        f.write(' ')
    print(f'Created: {p}')