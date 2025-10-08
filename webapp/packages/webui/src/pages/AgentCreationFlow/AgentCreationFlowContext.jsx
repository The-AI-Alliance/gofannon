import React, { createContext, useState, useContext } from 'react';
import PropTypes from 'prop-types';

export const AgentCreationFlowContext = createContext();

export const useAgentFlow = () => {
    const context = useContext(AgentCreationFlowContext);
    if (context === undefined) {
        throw new Error('useAgentFlow must be used within an AgentCreationFlowProvider');
    }
    return context;
};

export const AgentCreationFlowProvider = ({ children }) => {
    const [tools, setTools] = useState({}); // { "url": [] }
    const [description, setDescription] = useState('');
    const [inputSchema, setInputSchema] = useState({ inputText: "string" }); // Default JSON structure
    const [outputSchema, setOutputSchema] = useState({ outputText: "string" }); // Default JSON structure
    const [generatedCode, setGeneratedCode] = useState('');
    const [invokableModels, setInvokableModels] = useState([]);

    const value = {
        tools,
        setTools,
        description,
        setDescription,
        inputSchema,
        setInputSchema,
        outputSchema,
        setOutputSchema,
        generatedCode,
        setGeneratedCode,
        invokableModels,
        setInvokableModels,
    };

    return (
        <AgentCreationFlowContext.Provider value={value}>
            {children}
        </AgentCreationFlowContext.Provider>
    );
};

AgentCreationFlowProvider.propTypes = {
    children: PropTypes.node.isRequired,
};
