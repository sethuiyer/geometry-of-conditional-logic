import numpy as np

# ---------------------------------------------------------
# 1. THE DIFFERENTIABLE GARNER ESCAPEMENT
# ---------------------------------------------------------
def mod_inverse(a, m):
    a = a % m
    for x in range(1, m):
        if (a * x) % m == 1:
            return x
    return 1

def garners_target(a_list, p_list):
    """
    The 'Teleporter'. 
    Calculates the exact Master Coordinate X using Garner's Algorithm.
    This is what the podcast meant by 'navigating' with Garner's.
    """
    v = [0] * len(p_list)
    v[0] = a_list[0] % p_list[0]
    
    for i in range(1, len(p_list)):
        # Calculate product of previous primes
        prod_prev = 1
        for j in range(i):
            prod_prev *= p_list[j]
        
        # Calculate intermediate v_i
        inv_prod = mod_inverse(prod_prev, p_list[i])
        
        # This part is essentially a series of subtractions and multiplications
        # which are all differentiable if a_list were continuous.
        temp = a_list[i]
        for j in range(i):
            p_ij = 1
            for k in range(j):
                p_ij *= p_list[k]
            temp -= v[j] * p_ij
        
        v[i] = (temp * inv_prod) % p_list[i]
    
    # Reconstruct X
    X = v[0]
    p_acc = 1
    for i in range(1, len(p_list)):
        p_acc *= p_list[i-1]
        X += v[i] * p_acc
    return X

# ---------------------------------------------------------
# 2. THE CHALLENGE: 7 PRIMES (SOLVED VIA GARNER)
# ---------------------------------------------------------
primes = [2, 3, 5, 7, 11, 13, 17]
target_logic = [1, 0, 1, 1, 0, 1, 0]

# Use Garner's to find the 'Safe Corridor' target
master_target = garners_target(target_logic, primes)
print(f"Garner's calculated Master Target: {master_target}")

# ---------------------------------------------------------
# 3. THE NN (SIMPLE AGAIN, BECAUSE THE PATH IS CLEAR)
# ---------------------------------------------------------
class GarnerNavigatedNN:
    def __init__(self, input_size, hidden_size):
        self.W1 = np.random.randn(input_size, hidden_size) * 0.01
        self.b1 = np.zeros((1, hidden_size))
        self.W2 = np.random.randn(hidden_size, 1) * 0.01
        # Start the bias near the target to show the 'Snap'
        self.b2 = np.array([[master_target + np.random.uniform(-100, 100)]])

    def forward(self, X):
        self.X = X
        self.z1 = np.dot(X, self.W1) + self.b1
        self.a1 = np.tanh(self.z1) # Smooth activation
        self.z2 = np.dot(self.a1, self.W2) + self.b2
        return self.z2[0, 0]

    def train(self, X, target, lr):
        self.X = X
        z_pred = self.forward(self.X)
        loss = 0.5 * (z_pred - target)**2
        
        # dL/dz2 = (z_pred - target)
        grad = (z_pred - target)
        
        # Backprop with Gradient Clipping
        dW2 = np.dot(self.a1.T, np.array([[grad]]))
        db2 = np.array([[grad]])
        da1 = np.dot(np.array([[grad]]), self.W2.T)
        dz1 = da1 * (1 - self.a1**2)
        dW1 = np.dot(self.X.T, dz1)
        db1 = dz1

        # Clip gradients to prevent explosion
        max_grad = 100.0
        for g in [dW1, db1, dW2, db2]:
            np.clip(g, -max_grad, max_grad, out=g)
        
        # Simple SGD
        self.W1 -= lr * dW1
        self.b1 -= lr * db1
        self.W2 -= lr * dW2
        self.b2 -= lr * db2
        
        return loss, z_pred

# ---------------------------------------------------------
# EXECUTION
# ---------------------------------------------------------
nn = GarnerNavigatedNN(input_size=10, hidden_size=32)
X_input = np.random.randn(1, 10)

# SMALL learning rate because the target is huge
lr = 1e-4 

print("\nStarting Stabilized Garner-Navigated Training...")
for epoch in range(1000):
    loss, z_pred = nn.train(X_input, master_target, lr)
    if epoch % 200 == 0:
        print(f"Epoch {epoch:4d} | Net Output: {z_pred:10.2f} | Loss: {loss:10.4f}")
    if loss < 1e-4:
        print(f"\nLanding successful at epoch {epoch}!")
        break

final_z = nn.forward(X_input)
extracted = [int(round(final_z)) % p for p in primes]

print("\n--- Final Results ---")
print(f"Target Coordinate: {master_target}")
print(f"Network Output:    {final_z:.4f}")
print(f"Extracted Logic:   {extracted}")

if extracted == target_logic:
    print("\nSUCCESS: Garner's Algorithm provided the 'Safe Corridor'. Maze solved.")
