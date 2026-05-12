import numpy as np

# ---------------------------------------------------------
# 1. MATHEMATICAL CORE: PRIME TOPOLOGY
# ---------------------------------------------------------

def prime_wave_loss(z, targets, primes):
    """
    Computes the loss and its gradient for the Prime Topology.
    z: scalar (prediction)
    targets: list of target logic states (0 or 1)
    primes: list of prime numbers encoding the logic
    """
    loss = 0
    dz = 0
    for a, p in zip(targets, primes):
        phase = 2 * np.pi * (z - a) / p
        loss += (1 - np.cos(phase))
        # dL/dz = sin(phase) * (2*pi / p)
        dz += np.sin(phase) * (2 * np.pi / p)
    
    return loss, dz

# ---------------------------------------------------------
# 2. NUMPY NEURAL NETWORK (THE "HIKER")
# ---------------------------------------------------------

class PrimeNN:
    def __init__(self, input_size, hidden_size):
        # 2 Hidden layers for better representation
        self.W1 = np.random.randn(input_size, hidden_size) * np.sqrt(2. / input_size)
        self.b1 = np.zeros((1, hidden_size))
        self.W2 = np.random.randn(hidden_size, hidden_size) * np.sqrt(2. / hidden_size)
        self.b2 = np.zeros((1, hidden_size))
        self.W3 = np.random.randn(hidden_size, 1) * np.sqrt(2. / hidden_size)
        
        # Initialize output bias to search a wider range [0, 30]
        self.b3 = np.array([[np.random.uniform(0, 30)]])
        
        # Adam parameters
        self.params = [self.W1, self.b1, self.W2, self.b2, self.W3, self.b3]
        self.m = [np.zeros_like(p) for p in self.params]
        self.v = [np.zeros_like(p) for p in self.params]
        self.t = 0

    def relu(self, x):
        return np.maximum(0, x)

    def relu_deriv(self, x):
        return (x > 0).astype(float)

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
        
        # Output layer
        dW3 = np.dot(self.a2.T, np.array([[dL_dz3]]))
        db3 = np.array([[dL_dz3]])
        
        # Hidden layer 2
        da2 = np.dot(np.array([[dL_dz3]]), self.W3.T)
        dz2 = da2 * self.relu_deriv(self.z2)
        dW2 = np.dot(self.a1.T, dz2)
        db2 = dz2
        
        # Hidden layer 1
        da1 = np.dot(dz2, self.W2.T)
        dz1 = da1 * self.relu_deriv(self.z1)
        dW1 = np.dot(self.X.T, dz1)
        db1 = dz1

        # Gradients list
        grads = [dW1, db1, dW2, db2, dW3, db3]
        
        # Adam Update
        beta1, beta2, epsilon = 0.9, 0.999, 1e-8
        
        for i in range(len(self.params)):
            g = grads[i]
            self.m[i] = beta1 * self.m[i] + (1 - beta1) * g
            self.v[i] = beta2 * self.v[i] + (1 - beta2) * (g**2)
            m_hat = self.m[i] / (1 - beta1**self.t)
            v_hat = self.v[i] / (1 - beta2**self.t)
            self.params[i] -= lr * m_hat / (np.sqrt(v_hat) + epsilon)

# ---------------------------------------------------------
# 3. TRAINING: LEARNING SYMBOLIC CONSTRAINTS
# ---------------------------------------------------------

primes = [2, 3, 5]
target_logic = [1, 0, 1] 

input_dim = 10
hidden_dim = 64
lr = 0.05
epochs = 3000

X = np.random.randn(1, input_dim)
nn = PrimeNN(input_dim, hidden_dim)

print(f"Goal: Learn Logic {target_logic} using Primes {primes}")
print("Starting Adam descent down the Riemann manifold...\n")

best_loss = float('inf')
best_z = 0

for epoch in range(epochs):
    z_pred = nn.forward(X)
    loss, dL_dz = prime_wave_loss(z_pred, target_logic, primes)
    nn.backward(dL_dz, lr)
    
    if loss < best_loss:
        best_loss = loss
        best_z = z_pred
    
    if epoch % 300 == 0:
        print(f"Epoch {epoch:4d} | Output 'z': {z_pred:8.4f} | Loss: {loss:10.6f} | Best Loss: {best_loss:10.6f}")
    
    if loss < 1e-6:
        print(f"\nConvergence reached at epoch {epoch}!")
        break

# ---------------------------------------------------------
# 4. FINAL VERIFICATION
# ---------------------------------------------------------
final_z = best_z
print("\n--- Final Results (Best State) ---")
print(f"Network settled at coordinate z: {final_z:.4f}")

# Extract logic using modulo
extracted = [int(round(final_z)) % p for p in primes]
print(f"Target Logic:    {target_logic}")
print(f"Extracted Logic: {extracted}")

if extracted == target_logic:
    print("\nSUCCESS: The neural network has learned the symbolic constraints!")
else:
    print("\nFAILURE: Convergence not reached. Try running again or tweaking params.")
