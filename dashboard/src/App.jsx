import React, { useState, useEffect } from 'react';
import { Plus, Bell, TrendingDown, ExternalLink, Trash2, RefreshCw, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { supabase } from './supabase';

function App() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({ name: '', url: '', target_price: '' });

  useEffect(() => {
    fetchProducts();
  }, []);

  async function fetchProducts() {
    setLoading(true);
    const { data, error } = await supabase
      .from('products')
      .select('*')
      .order('created_at', { ascending: false });

    if (!error) setProducts(data);
    setLoading(false);
  }

  async function handleAddProduct(e) {
    e.preventDefault();
    const { error } = await supabase.from('products').insert([
      {
        name: formData.name,
        url: formData.url,
        target_price: parseFloat(formData.target_price) || null,
        last_price: 0,
        current_price: 0
      }
    ]);

    if (!error) {
      setFormData({ name: '', url: '', target_price: '' });
      setIsModalOpen(false);
      fetchProducts();
    }
  }

  async function handleDelete(id) {
    const { error } = await supabase.from('products').delete().eq('id', id);
    if (!error) fetchProducts();
  }

  return (
    <div className="min-h-screen p-4 md:p-8">
      {/* Header */}
      <header className="max-w-7xl mx-auto flex justify-between items-center mb-12">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-white to-gray-500 bg-clip-text text-transparent">
            SkyWatch Prices
          </h1>
          <p className="text-gray-400 mt-1">Monitoramento inteligente de ofertas</p>
        </div>
        <div className="flex gap-4">
          <button onClick={fetchProducts} className="p-3 glass-card hover:bg-white/10 transition-colors">
            <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
          </button>
          <button onClick={() => setIsModalOpen(true)} className="glow-button flex items-center gap-2">
            <Plus size={20} />
            <span>Adicionar</span>
          </button>
        </div>
      </header>

      {/* Product Grid */}
      <main className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {loading && products.length === 0 ? (
          <div className="col-span-full py-20 text-center text-gray-500">Carregando seus produtos...</div>
        ) : products.length === 0 ? (
          <div className="col-span-full py-20 text-center text-gray-500">Nenhum produto sendo monitorado. Clique em Adicionar!</div>
        ) : (
          <AnimatePresence>
            {products.map((product) => (
              <motion.div
                key={product.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="glass-card group overflow-hidden"
              >
                <div className="p-6">
                  <h3 className="text-xl font-bold mb-4">{product.name}</h3>
                  <div className="flex justify-between items-end mb-6">
                    <div>
                      <p className="text-gray-400 text-sm">Preço Atual</p>
                      <p className="text-2xl font-bold text-white">R$ {product.current_price?.toLocaleString() || '---'}</p>
                    </div>
                    {product.last_price > product.current_price && (
                      <div className="bg-green-500/20 text-green-400 px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1">
                        <TrendingDown size={14} /> BAIXOU
                      </div>
                    )}
                  </div>

                  <div className="space-y-2 mb-6 text-sm text-gray-400">
                    <div className="flex justify-between">
                      <span>Alvo:</span>
                      <span className="text-indigo-400 font-bold">R$ {product.target_price?.toLocaleString() || '-'}</span>
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <a href={product.url} target="_blank" className="flex-1 glass-card py-2 text-sm font-semibold hover:bg-white/10 transition-all flex items-center justify-center gap-2 border-none">
                      <ExternalLink size={16} /> Link
                    </a>
                    <button onClick={() => handleDelete(product.id)} className="p-2 glass-card hover:bg-red-500/10 text-red-400 border-none transition-all">
                      <Trash2 size={18} />
                    </button>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </main>

      {/* Modal */}
      <AnimatePresence>
        {isModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setIsModalOpen(false)} className="absolute inset-0 bg-black/80 backdrop-blur-sm" />
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }} className="glass-card w-full max-w-md p-8 relative z-10 bg-zinc-900" >
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold">Novo Produto</h2>
                <button onClick={() => setIsModalOpen(false)}><X size={20} /></button>
              </div>
              <form onSubmit={handleAddProduct} className="space-y-4">
                <div>
                  <label className="text-sm text-gray-400 block mb-2">URL do Produto</label>
                  <input required value={formData.url} onChange={e => setFormData({ ...formData, url: e.target.value })} type="url" className="input-field" placeholder="https://..." />
                </div>
                <div>
                  <label className="text-sm text-gray-400 block mb-2">Nome amigável</label>
                  <input required value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} type="text" className="input-field" placeholder="Ex: Monitor gamer" />
                </div>
                <div>
                  <label className="text-sm text-gray-400 block mb-2">Preço Alvo (Opcional)</label>
                  <input value={formData.target_price} onChange={e => setFormData({ ...formData, target_price: e.target.value })} type="number" className="input-field" placeholder="R$ 1.500" />
                </div>
                <button type="submit" className="glow-button w-full mt-4 py-4">Salvar no Monitor</button>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
