MATCH (n) DETACH DELETE n;

CREATE (mlflow:`Root` {
    name: "MLflow"
});



CREATE (flexibility:`Philosophy` {
    name: "Flexibility"
});
MATCH (source), (target)
WHERE source.name = "MLflow" AND target.name = "Flexibility"
CREATE (source)-[r:`core philosophy`]->(target) RETURN type(r);



CREATE (tracking:`Main Component` {
    name: "Tracking"
});
CREATE (projects:`Main Component` {
    name: "Projects"
});
CREATE (models:`Main Component` {
    name: "Models"
});
CREATE (modelRegistry:`Main Component` {
    name: "Model Registry"
});
MATCH (source), (target)
WHERE source.name = "MLflow" AND target.name = "Tracking"
CREATE (source)-[r:`main component`]->(target) RETURN type(r);
MATCH (source), (target)
WHERE source.name = "MLflow" AND target.name = "Projects"
CREATE (source)-[r:`main component`]->(target) RETURN type(r);
MATCH (source), (target)
WHERE source.name = "MLflow" AND target.name = "Models"
CREATE (source)-[r:`main component`]->(target) RETURN type(r);
MATCH (source), (target)
WHERE source.name = "MLflow" AND target.name = "Model Registry"
CREATE (source)-[r:`main component`]->(target) RETURN type(r);



CREATE (productiveML:`Business Goal` {
    name: "Productive Machine Learning"
});
CREATE (trackingExperiments:`Business Goal` {
    name: "Tracking Experiments"
});
CREATE (reproduceCode:`Business Goal` {
    name: "Code Sharing"
});
CREATE (modelStandard:`Business Goal` {
    name: "Model Packaging & Deploying Standards"
});
CREATE (modelMgmt:`Business Goal` {
    name: "Model Central Management"
});
MATCH (source), (target)
WHERE source.name = "Productive Machine Learning" AND target.name = "Tracking Experiments"
CREATE (source)-[r:`challenge`]->(target) RETURN type(r);
MATCH (source), (target)
WHERE source.name = "Productive Machine Learning" AND target.name = "Code Sharing"
CREATE (source)-[r:`challenge`]->(target) RETURN type(r);
MATCH (source), (target)
WHERE source.name = "Productive Machine Learning" AND target.name = "Model Packaging & Deploying Standards"
CREATE (source)-[r:`challenge`]->(target) RETURN type(r);
MATCH (source), (target)
WHERE source.name = "Productive Machine Learning" AND target.name = "Model Central Management"
CREATE (source)-[r:`challenge`]->(target) RETURN type(r);



MATCH (source), (target)
WHERE source.name = "Tracking" AND target.name = "Tracking Experiments"
CREATE (source)-[r:`solution for`]->(target) RETURN type(r);
MATCH (source), (target)
WHERE source.name = "Projects" AND target.name = "Code Sharing"
CREATE (source)-[r:`solution for`]->(target) RETURN type(r);
MATCH (source), (target)
WHERE source.name = "Models" AND target.name = "Model Packaging & Deploying Standards"
CREATE (source)-[r:`solution for`]->(target) RETURN type(r);
MATCH (source), (target)
WHERE source.name = "Model Registry" AND target.name = "Model Central Management"
CREATE (source)-[r:`solution for`]->(target) RETURN type(r);



CREATE (runOnDistributedCluster:`Scalability` {
    name: "Run ML on Distributed Cluster"
});
CREATE (parallelRun:`Scalability` {
    name: "Run ML in Parallel"
});
CREATE (externalizeDataSource:`Scalability` {
    name: "Externalize data storage"
});
MATCH (source), (target)
WHERE source.name = "MLflow" AND target.name = "Run ML on Distributed Cluster"
CREATE (source)-[r:`scales by`]->(target) RETURN type(r);
MATCH (source), (target)
WHERE source.name = "MLflow" AND target.name = "Run ML in Parallel"
CREATE (source)-[r:`scales by`]->(target) RETURN type(r);
MATCH (source), (target)
WHERE source.name = "MLflow" AND target.name = "Externalize data storage"
CREATE (source)-[r:`scales by`]->(target) RETURN type(r);
MATCH (source), (target)
WHERE source.name = "MLflow" AND target.name = "Model Registry"
CREATE (source)-[r:`scales by`]->(target) RETURN type(r);
