import React, { createContext, useContext } from 'react';
import PropTypes from 'prop-types';
import appConfig from '../config';

// 1. Create the context
export const ConfigContext = createContext();

// 2. Create a custom hook for easy consumption
export const useConfig = () => {
    const context = useContext(ConfigContext);
    if (context === undefined) {
        throw new Error('useConfig must be used within a ConfigProvider');
    }
    return context;
};

// 3. Create the provider component
export const ConfigProvider = ({ children }) => {
    const value = { config: appConfig };

    return (
        <ConfigContext.Provider value={value}>
            {children}
        </ConfigContext.Provider>
    );
};

ConfigProvider.propTypes = {
    children: PropTypes.node.isRequired,
};