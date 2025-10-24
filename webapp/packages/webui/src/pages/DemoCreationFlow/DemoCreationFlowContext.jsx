// webapp/packages/webui/src/pages/DemoCreationFlow/DemoCreationFlowContext.jsx
import React, { createContext, useState, useContext } from 'react';
import PropTypes from 'prop-types';

export const DemoCreationFlowContext = createContext();

export const useDemoFlow = () => {
    const context = useContext(DemoCreationFlowContext);
    if (context === undefined) {
        throw new Error('useDemoFlow must be used within a DemoCreationFlowProvider');
    }
    return context;
};

export const DemoCreationFlowProvider = ({ children }) => {
    const [selectedApis, setSelectedApis] = useState([]);
    const [modelConfig, setModelConfig] = useState(null);
    const [userPrompt, setUserPrompt] = useState('');
    const [generatedCode, setGeneratedCode] = useState({ html: '', css: '', js: '' });
    const [appName, setAppName] = useState('');
    const [description, setDescription] = useState('');

    const value = {
        selectedApis,
        setSelectedApis,
        modelConfig,
        setModelConfig,
        userPrompt,
        setUserPrompt,
        generatedCode,
        setGeneratedCode,
        appName,
        setAppName,
        description,
        setDescription,       
    };

    return (
        <DemoCreationFlowContext.Provider value={value}>
            {children}
        </DemoCreationFlowContext.Provider>
    );
};

DemoCreationFlowProvider.propTypes = {
    children: PropTypes.node.isRequired,
};