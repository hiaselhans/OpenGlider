#pragma once

#include<vector>
#include <algorithm>    // std::max
#include <memory>

#include "euklid/vector/vector.hpp"


template<typename VectorType, typename T>
    class PolyLine {
        public:
            PolyLine();
            PolyLine(std::vector<std::shared_ptr<VectorType>>&);

            std::shared_ptr<VectorType> get(double ik);

            std::shared_ptr<VectorType> __getitem__(int i);
            void __setitem__(std::shared_ptr<VectorType> item);

            int __len__();
            double get_length();
            std::vector<std::shared_ptr<VectorType>> get_segments();
            std::vector<double> get_segment_lengthes();
            
            double walk(double start, double amount);

            std::vector<std::shared_ptr<VectorType>> nodes;
            T resample(int num_points);
            T copy();
            T scale(const VectorType&);
            T scale(const double);
        
        private:
            std::string hash;
            
    };

class PolyLine3D : public PolyLine<Vector3D, PolyLine3D> {
    public:
        using PolyLine<Vector3D, PolyLine3D>::PolyLine;
};
