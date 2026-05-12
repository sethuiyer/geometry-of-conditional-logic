import numpy as np

# ---------------------------------------------------------
# THE 5-DIMENSIONAL PRIME MAZE
# ---------------------------------------------------------
# Search space: 0 to 2,310
primes = [2, 3, 5, 7, 11]
target_logic = [1, 0, 1, 0, 1]

def prime_wave_loss(z, targets, primes):
    loss = 0
    dz = 0
    for a, p in zip(targets, primes):
        phase = 2 * np.pi * (z - a) / p
        loss += (1 - np.cos(phase))
        dz += np.sin(phase) * (2 * np.pi / p)
    return loss, dz

class RobustPrimeNN:
    def __init__(self, input_size, hidden_size):
        self.W1 = np.random.randn(input_size, hidden_size) * np.sqrt(2. / input_size)
        self.b1 = np.zeros((1, hidden_size))
        self.W2 = np.random.randn(hidden_size, hidden_size) * np.sqrt(2. / hidden_size)
        self.b2 = np.zeros((1, hidden_size))
        self.W3 = np.random.randn(hidden_size, 1) * np.sqrt(2. / hidden_size)
        
        # Start searching in the [0, 2310] range
        self.b3 = np.array([[np.random.uniform(0, 2310)]])
        
        self.params = [self.W1, self.b1, self.W2, self.b2, self.W3, self.b3]
        self.m = [np.zeros_like(p) for p in self.params]
        self.v = [np.zeros_like(p) for p in self.params]
        self.t = 0

    def relu(self, x): return np.maximum(0, x)
    def relu_deriv(self, x): return (x > 0).astype(float)

    def forward(self, X):
        self.X = X
        self.z1 = np.dot(X, self.W1) + self.b1
        self.a1 = self.relu(self.z1)
        self.z2 = np.dot(self.a1, self.W2) + self.b2
        self.a2 = self.relu(self.z2)
        self.z3 = np.dot(self.a2, self.W3) + self.b3
        return self.z3[0, 0]

    def backward(self, dL_dz3, lr):
        self.t += 1
        dW3 = np.dot(self.a2.T, np.array([[dL_dz3]]))
        db3 = np.array([[dL_dz3]])
        da2 = np.dot(np.array([[dL_dz3]]), self.W3.T)
        dz2 = da2 * self.relu_deriv(self.z2)
        dW2 = np.dot(self.a1.T, dz2)
        db2 = dz2
        da1 = np.dot(dz2, self.W2.T)
        dz1 = da1 * self.relu_deriv(self.z1)
        dW1 = np.dot(self.X.T, dz1)
        db1 = dz1

        grads = [dW1, db1, dW2, db2, dW3, db3]
        beta1, beta2, epsilon = 0.9, 0.999, 1e-8
        
        for i in range(len(self.params)):
            g = grads[i]
            self.m[i] = beta1 * self.m[i] + (1 - beta1) * g
            self.v[i] = beta2 * self.v[i] + (1 - beta2) * (g**2)
            m_hat = self.m[i] / (1 - beta1**self.t)
            v_hat = self.v[i] / (1 - beta2**self.t)
            self.params[i] -= lr * m_hat / (np.sqrt(v_hat) + epsilon)

# ---------------------------------------------------------
# EXECUTION
# ---------------------------------------------------------
input_dim = 10
hidden_dim = 64
base_lr = 0.1
epochs = 5000

X = np.random.randn(1, input_dim)
nn = RobustPrimeNN(input_dim, hidden_dim)

print(f"DIFFICULT PROBLEM: Learn Logic {target_logic} across 5 Prime Dimensions.")
print(f"Search Space: 0 to {np.prod(primes)}")

best_loss = float('inf')
best_z = 0

for epoch in range(epochs):
    # Cyclic Learning Rate to escape local minima
    lr = base_lr * (0.5 * (1 + np.cos(epoch * np.pi / 500)))
    
    z_pred = nn.forward(X)
    loss, dL_dz = prime_wave_loss(z_pred, target_logic, primes)
    nn.backward(dL_dz, lr)
    
    if loss < best_loss:
        best_loss = loss
        best_z = z_pred
    
    if epoch % 500 == 0:
        print(f"Epoch {epoch:5d} | Output 'z': {z_pred:8.2f} | Loss: {loss:8.4f} | LR: {lr:.4f}")
    
    if loss < 1e-7:
        print(f"\nCONVERGENCE REACHED AT EPOCH {epoch}!")
        break

# FINAL VALIDATION
final_z = best_z
extracted = [int(round(final_z)) % p for p in primes]
print("\n--- Final Results ---")
print(f"Network found Coordinate: {final_z:.4f}")
print(f"Target Logic:    {target_logic}")
print(f"Extracted Logic: {extracted}")

if extracted == target_logic:
    print("\nSUCCESS: The AI successfully navigated the 7D Prime Maze!")
else:
    print("\nFAILURE: The maze was too complex. Local minimum trapped the hiker.")
