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
    const [swaggerSpecs, setSwaggerSpecs] = useState([]); // [{ name: string, content: string }]
    const [description, setDescription] = useState('');
    const [inputSchema, setInputSchema] = useState({ inputText: "string" }); 
    const [outputSchema, setOutputSchema] = useState({ outputText: "string" });
    const [generatedCode, setGeneratedCode] = useState('');
    const [friendlyName, setFriendlyName] = useState('');
    const [docstring, setDocstring] = useState('');
    const [invokableModels, setInvokableModels] = useState([]);
    const [gofannonAgents, setGofannonAgents] = useState([]); // {id, name}

    // State for the composer model's built-in tool
    const [composerBuiltInTool, setComposerBuiltInTool] = useState('');    

    const value = {
        tools,
        setTools,
        swaggerSpecs,
        setSwaggerSpecs,
        description,
        setDescription,
        inputSchema,
        setInputSchema,
        outputSchema,
        setOutputSchema,
        generatedCode,
        setGeneratedCode,
        friendlyName,
        setFriendlyName,
        docstring,
        setDocstring,
        invokableModels,
        setInvokableModels,
        gofannonAgents,
        setGofannonAgents,
        composerBuiltInTool,
        setComposerBuiltInTool,       
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
